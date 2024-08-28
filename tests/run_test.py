#!/usr/bin/env python
import os
import shutil
import sys
import logging
import tempfile
from subprocess import CalledProcessError, STDOUT, check_output
from jsonschema import Draft4Validator, validators, FormatChecker
from .lib.cnat_cfggen import CfgGen
from .lib.common import run_cmd, load_yaml_file, read_file, write_file, valid_resource


class RunTests:
    def __init__(self, resource='all', debug=True):
        self.root_path = sys.path[0]
        self.is_auto = True
        self.debug = debug
        self.resource = resource.split(',')

    def get_test_cases(self):
        self.debug and print(f"Going to verify changes and get test cnf and version.")
        git_cmd = "git log -1 --name-only | grep templates/"
        try:
            changed_files = run_cmd(cmd=git_cmd).split('\n')
        except Exception as ex:
            # if none code change in templates/, it would fail as below.
            if "git log -1 --name-only | grep templates/ failed with: []" in str(ex):
                changed_files = []
            else:
                raise ex
        case_list = {}
        for path in changed_files:
            path = path.split('/')
            if path[0] == 'templates' and path[1] != 'common':
                if path[1] not in case_list:
                    case_list[path[1]]=[path[2]]
                elif path[2] not in case_list[path[1]]:
                    case_list[path[1]].append(path[2])
                else:
                    pass

        if len(case_list) == 0 or \
                (len(case_list) == 1 and
                 len(case_list[list(case_list.keys())[0]]) == 1):
            self.debug and print(f"Going to test {case_list} cases.")
            return case_list
        else:
            error_msg = f""
            for cnf in case_list.keys():
                error_msg += f"CNF:{cnf} with version: {case_list[cnf]}\n"
            raise Exception(f"Only one version in one cnf should be changed in one commit.\n\
                Following changes are made:\n{error_msg}")

    def collect_resource(self, cnf_info, resource):
        """
        resource_info:{
                        'nfvi':
                        {
                                'repo': '5gc_config/5gc_sa_pkg'
                                'cnat': '/lab/pccc_utils/scripts/src/bin/cnat'
                                'pcc':
                                [
                                    {
                                        version: 1.25
                                        branch: release-1.10
                                        cfggen: lab/n99/eccd1/pcc1/cfggen.yaml
                                    }
                                ]
                            }
                        }
        """
        self.debug and print(f"Start to collect {cnf_info} case resources.")
        resource_path = os.path.join(self.root_path, 'tests/resources')
        resource_info = {}
        for key in cnf_info:
            cnf_name = key
            version = cnf_info[key][0]
        for yml in os.listdir(resource_path):
            resource_name = yml.split('.')[0]
            if (yml.endswith('.yaml') or yml.endswith('.yml')) \
                    and (resource[0] == 'all' or resource_name in resource):
                resource_content = load_yaml_file(os.path.join(resource_path, yml))
                try:
                    schema_path = os.path.join(self.root_path, f'tests/lib/schema.yaml')
                    valid_resource(resource_content, schema_path, yml, self.debug)
                except Exception as ex:
                    resource_info[resource_name] = {'error': str(ex)}
                    continue
                repo_get = False
                case_info = {}
                for cnf in resource_content:
                    if cnf == cnf_name:
                        for case in resource_content[cnf]:
                            if case['version'] == version:
                                if not repo_get:
                                    case_info['repo'] = resource_content['repoProjectName']
                                    case_info['cnat'] = resource_content['cnatBinaryPath']
                                    repo_get = True
                                if not case_info.get(cnf):
                                    case_info[cnf] = [case]
                                else:
                                    case_info[cnf].append(case)
                if case_info:
                    self.debug and print(f"Collected case '{resource_name}' with {case_info}")
                    resource_info[resource_name] = case_info
        return resource_info

    def download_resource(self, case_name, repo_info):
        self.debug and print(f"Downloading resource for {case_name}")
        git_path = os.path.join(self.temp_path, case_name)
        git_clone = f"git clone https://gerrit-gamma.gic.ericsson.se/a/{repo_info} {git_path}"
        self.debug and print(f"Running cmd: {git_clone}")
        run_cmd(cmd=git_clone)
        return git_path

    def reset_commit(self, resource_path, case):
        branch = case.get('branch')
        self.debug and print(f"Checking out branch to: {branch}")
        git_cmd = f"git checkout {branch}"
        self.debug and print(f"Running cmd: {git_cmd}")
        run_cmd(cmd=git_cmd, cwd=resource_path)

        if commit_id := case.get('commitId'):
            self.debug and print(f"Resetting commit to: {commit_id}")
            git_cmd = f"git reset --hard {commit_id}"
            self.debug and print(f"Running cmd: {git_cmd}")
            run_cmd(cmd=git_cmd, cwd=resource_path)
        else:
            self.debug and print(f"Resetting commit to latest commit")
            git_cmd = "git pull -r"
            self.debug and print(f"Running cmd: {git_cmd}")
            run_cmd(cmd=git_cmd, cwd=resource_path)
        return

    def change_value_file(self, value_path):
        content = read_file(value_path)
        for i in range(len(content)):
            if 'adminpasswd: ' in content[i]:
                del content[i]
                break
        write_file(content, value_path)
        return

    def compare_pretreatment(self, test_path, expected_outputs, target_path):
        self.debug and print('Going to do pretreatment for files:', expected_outputs)
        for file in os.listdir(test_path):
            if 'values.yaml' in file:
                value_path = os.path.join(test_path, file)
                self.change_value_file(value_path)
        for file in expected_outputs:
            if 'values.yaml' in file:
                value_path = os.path.join(target_path, file)
                self.change_value_file(value_path)
        return

    def compare_files(self, expected_outputs, tmp_test, target_path):
        self.debug and print('Going to prepare files:', expected_outputs)
        res = 'Pass'
        diff_out = ''
        for output in expected_outputs:
            test_file_path = os.path.join(tmp_test, output)
            expect_file_path = os.path.join(target_path, output)
            try:
                cmd = f"diff -uB {expect_file_path} {test_file_path}"
                self.debug and print(f"Running cmd: {cmd}")
                check_output(cmd.split())
            except CalledProcessError as ex:
                res = 'Fail'
                diff_out+=ex.stdout.decode()
            # fail here to avoid the exception traceback from pytest
        return res, diff_out

    def getExpectedOutputs(self, resource_path, cfggen_path, cnf_info):
        self.debug and print('Getting expected output from', cfggen_path)
        expectedOutputs = []
        for item in cnf_info:
            case_relate = f"{item}/{cnf_info[item][0]}"
        cfggen = load_yaml_file(os.path.join(resource_path, cfggen_path))
        for item in cfggen['files']:
            if case_relate in item['template']:
                expectedOutputs.append(item['target'])
        return expectedOutputs

    def run_case(self, resource_path, case, cnat_path, cnf_info):
        self.debug and print('Running case with cfggen: ', case['cfggen'])
        cfggen_path = os.path.join(resource_path, case['cfggen'])
        templates_dir = os.path.join(self.root_path, 'templates')
        with tempfile.TemporaryDirectory() as tmp_test:
            cfggen = CfgGen(cfggen_path, templates_dir, cnat_path, tmp_test)
            result = cfggen.generate_config()
            self.debug and print(result)
            target_path = os.path.dirname(os.path.join(resource_path, cfggen_path))
            expectedOutputs = self.getExpectedOutputs(resource_path, case['cfggen'], cnf_info)
            self.compare_pretreatment(tmp_test, expectedOutputs, target_path)
            res, diff_out = self.compare_files(expectedOutputs, tmp_test, target_path)
        return res, diff_out

    def run_tests(self, case_name, case_info, case_num, pass_num, cnf_info):
        # Summary the pass case [0] and fail case [1] for every resource.
        result = {'summary':[0, 0]}
        if case_info.get('error'):
            result['resource'] = [{'case_input': case_name,
                                   'case_result': "Error",
                                   'detail': case_info['error']}]
            result['summary'][1] = 1
            case_num += 1
            return result, case_num, pass_num
        try:
            resource_path = self.download_resource(case_name, case_info['repo'])
        except Exception as ex:
            result['repo'] = [{'case_input': case_info['repo'],
                               'case_result': "Error",
                               'detail': str(ex)}]
            result['summary'][1] = 1
            case_num += 1
            return result, case_num, pass_num

        cnat_path = case_info.pop('cnat')
        case_info.pop('repo')
        for cnf in case_info:
            case_result = []
            for case in case_info[cnf]:
                try:
                    self.reset_commit(resource_path, case)   # update commit id and branch
                    res, detail = self.run_case(resource_path, case, cnat_path, cnf_info)
                except Exception as ex:
                    res = "Error"
                    detail = str(ex)
                # rollback the expected output file change.
                git_cmd = "git checkout ."
                self.debug and print(f"Running cmd: {git_cmd}")
                run_cmd(cmd=git_cmd, cwd=resource_path)
                single_result = {'case_input': case['cfggen'],
                                 'case_result': res,
                                 'detail': detail}
                case_result.append(single_result)
                case_num += 1
                if res == 'Pass':
                    pass_num += 1
                    result['summary'][0] += 1
                else:
                    result['summary'][1] += 1
            result[cnf] = case_result
        return result, case_num, pass_num

    def test_main(self):
        cnf_info = self.get_test_cases()
        if len(cnf_info) == 0:
            self.debug and print(f"No case need to test.")
            return([], 0, 0)
        resource_info = self.collect_resource(cnf_info, self.resource)
        self.temp_path = tempfile.mkdtemp()
        result = {}
        case_num = 0
        pass_num = 0
        try:
            for case_name in resource_info:
                test_result, case_num, pass_num = \
                    self.run_tests(case_name,
                                   resource_info[case_name],
                                   case_num, pass_num, cnf_info)
                result[case_name] = test_result
        except Exception as ex:
            logging.error(ex)
        finally:
            shutil.rmtree(self.temp_path)
        return result, case_num, pass_num
