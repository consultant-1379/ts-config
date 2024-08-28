import pytest
from .run_test import RunTests


def output_result(result, total_case_num, total_passed_num):
    output = f""
    output += f"\n\n\n-----------------------------------------------------------------------------\n"
    output += f"\n                      Following are the test results\n\n"
    for resource in result:
        output += f"----------------------------------------------------------------------------\n"
        output += f"For cases in resource file {resource}:\n"
        for cnf in result[resource]:
            if cnf != 'summary':
                output += f"{cnf} cases:\n"
                for case in result[resource][cnf]:
                    if case['case_result'] == 'Fail':
                        output += f"Input: {case['case_input']}\tResult: {case['case_result']}\n"
                        output += f"Diff result between expected output and real output:\n"
                        output += f"{case['detail']}\n"
                    elif case['case_result'] == 'Error':
                        output += f"Input: {case['case_input']}\tResult: {case['case_result']}\n"
                        output += f"Case run failed for:\n"
                        output += f"{case['detail']}\n"
                    else:
                        output += f"Input: {case['case_input']}\tResult: {case['case_result']}\n"
    output += f"\n\n-----------------------------------------------------------------------------\n"
    output += f"                                  Summary\n"
    output += f"-----------------------------------------------------------------------------\n"
    fail_resource = []
    if total_passed_num < total_case_num:
        output += "\t"
    output += f"\t\tTotal\tPass\tFail\n"
    for resource in result:
        track_passed_num = result[resource]['summary'][0]
        track_failed_num = result[resource]['summary'][1]
        output += f"{resource}\t"
        # The max length for resource name that can keep the table format is 16.
        # The column length for shell is 8, for pytest is 12.
        if (total_passed_num == total_case_num and len(resource) < 8) or \
                (total_passed_num < total_case_num and len(resource) < 12):
            output += "\t"
        output += f"{track_passed_num + track_failed_num}\t{track_passed_num}\t{track_failed_num}\n"
        if track_failed_num > 0:
            fail_resource.append(resource)
    if len(fail_resource) > 0:
        output += f"{fail_resource} failed!\n"
    output += f"-----------------------------------------------------------------------------\n"
    return output


def test_config(get_cmdopts):
    result, case_num, pass_num = RunTests(resource=get_cmdopts['track'],
                                          debug=get_cmdopts['detail']).test_main()
    output = output_result(result, case_num, pass_num)
    if case_num > pass_num:
        raise Exception(output)
    else:
        print(output)


if __name__ == '__main__':
    pytest.main()
