"""Synthetic recovery regressions; no empirical source or test execution."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import recover_zpd_transition_evaluation as recovery
from scripts import run_zpd_transition_generation as core


def terminal(phase='generation'):
    return dict(Id=core.unit(phase), LoadState='loaded', Result='success', ExecMainCode='1',
                ExecMainStatus='0', MainPID='0', SubState='exited', ControlGroup='')


def group(phase='generation'):
    return f'/user.slice/user-{os.getuid()}.slice/user@{os.getuid()}.service/app.slice/{core.unit(phase)}'


class TerminalGroupTests(unittest.TestCase):
    def test_empty_property_is_requested_and_preserved(self):
        with patch.object(recovery.subprocess, 'check_output', return_value='ControlGroup=\nSubState=exited\n') as query:
            self.assertEqual(recovery.properties(core.unit('generation'))['ControlGroup'], '')
        self.assertIn('--all', query.call_args.args[0])

    def test_removed_group_with_explicit_empty_value_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            result = recovery.terminal_group(terminal(), group(), core.unit('generation'), Path(directory))
        self.assertTrue(result['cleanup_verified'])
        self.assertTrue(result['cgroup_removed'])

    def test_missing_property_is_not_silently_treated_as_empty(self):
        values = terminal(); values.pop('ControlGroup')
        with self.assertRaisesRegex(ValueError, 'absent evidence'):
            recovery.terminal_group(values, group(), core.unit('generation'))

    def test_wrong_unit_changed_group_and_unbound_path_refuse(self):
        for mutation in ('id', 'load', 'group', 'recorded'):
            with self.subTest(mutation=mutation):
                values = terminal(); recorded = group()
                if mutation == 'id': values['Id'] = 'other.service'
                if mutation == 'load': values['LoadState'] = 'not-found'
                if mutation == 'group': values['ControlGroup'] = '/other'
                if mutation == 'recorded': recorded = '/other/'+core.unit('generation')
                with self.assertRaises(ValueError):
                    recovery.terminal_group(values, recorded, core.unit('generation'))

    def test_existing_empty_group_passes_but_descendant_and_resource_events_refuse(self):
        for mutation in ('none', 'process', 'populated', 'memory', 'pids'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)/group().lstrip('/'); root.mkdir(parents=True)
                (root/'cgroup.procs').write_text('123\n' if mutation == 'process' else '')
                (root/'cgroup.events').write_text('populated '+('1' if mutation == 'populated' else '0')+'\n')
                (root/'memory.events').write_text('low 0\noom '+('1' if mutation == 'memory' else '0')+'\n')
                (root/'pids.events').write_text('max '+('1' if mutation == 'pids' else '0')+'\n')
                if mutation == 'none':
                    self.assertFalse(recovery.terminal_group(terminal(), group(), core.unit('generation'), Path(directory))['cgroup_removed'])
                else:
                    with self.assertRaises(ValueError):
                        recovery.terminal_group(terminal(), group(), core.unit('generation'), Path(directory))


class RecoveryScopeTests(unittest.TestCase):
    def test_no_generation_command_exists(self):
        with self.assertRaisesRegex(ValueError, 'cannot launch generation'):
            recovery.command(core, 'generation')
        for phase in ('public', 'private'):
            cmd = recovery.command(core, phase)
            self.assertIn('--property=WorkingDirectory='+str(recovery.ORIGINAL), cmd)
            self.assertIn('--property=RuntimeMaxSec=21600', cmd)
            self.assertEqual(cmd[cmd.index('--phase')+1], phase)
            self.assertEqual(cmd[-1], recovery.ORIGINAL_RELEASE_SHA)
            self.assertNotIn('supervise', cmd)

    def stage(self, family):
        output = family/'generation-v1'; output.mkdir()
        core.write_new(output/'stage-manifest.json', dict(revision=recovery.ORIGINAL_REVISION,
            release_sha256=recovery.ORIGINAL_RELEASE_SHA, envelope=dict(cgroup=group())))
        core.write_new(output/'payload.json', {'synthetic': True})
        core.seal_stage(output, 'generation', recovery.ORIGINAL_RELEASE_SHA)
        return output

    def test_certify_normal_exit_and_old_seal_without_changing_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            family = Path(directory); output = self.stage(family)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with patch.object(recovery, 'FAMILY', family), patch.object(recovery, 'properties', return_value=terminal()), \
                    patch.object(recovery.subprocess, 'run') as command:
                result = recovery.certify(core, 'generation', 'a'*64)
            self.assertEqual(result['complete_sha256'], core.sha_file(output/'STAGE_COMPLETE.json'))
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)
            self.assertTrue((family/'generation-VERIFIED_COMPLETE.json').exists())
            command.assert_called_once_with(['/usr/bin/systemctl', '--user', 'stop', core.unit('generation')], check=True, timeout=30)

    def test_abnormal_exit_tampered_output_or_missing_group_never_certifies_or_stops(self):
        for mutation in ('exit', 'tamper', 'missing_group'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                family = Path(directory); output = self.stage(family); values = terminal()
                if mutation == 'exit': values['ExecMainStatus'] = '1'
                if mutation == 'tamper': (output/'payload.json').write_text('changed')
                if mutation == 'missing_group': values.pop('ControlGroup')
                with patch.object(recovery, 'FAMILY', family), patch.object(recovery, 'properties', return_value=values), \
                        patch.object(recovery.subprocess, 'run') as command:
                    with self.assertRaises(ValueError): recovery.certify(core, 'generation', 'a'*64)
                    command.assert_not_called()
                self.assertFalse((family/'generation-VERIFIED_COMPLETE.json').exists())

    def test_preflight_refuses_existing_later_output_or_recovery_marker(self):
        for mutation in ('none', 'public', 'private', 'recovery', 'unit', 'wrong_failure'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                family = Path(directory); output = self.stage(family)
                failure = dict(completed_phases=[], error='terminal cgroup changed', error_type='ValueError')
                if mutation == 'wrong_failure': failure['error'] = 'different'
                pin = core.write_new(family/'COORDINATOR_FAILED.json', failure)
                release = dict(original_release_sha256=recovery.ORIGINAL_RELEASE_SHA,
                    generation_complete_sha256=core.sha_file(output/'STAGE_COMPLETE.json'), remaining_phases=['public','private'],
                    generation_reexecution=False, preserved_evidence_sha256={'COORDINATOR_FAILED.json':pin})
                if mutation in ('public','private'): (family/(mutation+'-v1')).mkdir()
                if mutation == 'recovery': (family/'RECOVERY-v1.json').write_text('{}')
                def properties(name):
                    if name.endswith('coordinator.service'):
                        return dict(MainPID='0', ActiveState='failed', Result='exit-code', ExecMainStatus='1')
                    return dict(LoadState='loaded' if mutation == 'unit' else 'not-found')
                with patch.object(recovery,'FAMILY',family), patch.object(recovery,'GENERATION_SHA',release['generation_complete_sha256']), \
                        patch.object(recovery,'properties',side_effect=properties):
                    if mutation == 'none': recovery.preflight(core, release)
                    else:
                        with self.assertRaises(ValueError): recovery.preflight(core, release)


if __name__ == '__main__': unittest.main()
