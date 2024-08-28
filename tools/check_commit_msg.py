import argparse
import re
from subprocess import check_output, STDOUT


class CheckCommitMsg():
    def main(self):
        self.get_parser()
        headline = self.check_headline()
        commit = self.check_commit()
        commom_cmd = 'ssh -p 29418 gerrit-gamma.gic.ericsson.se gerrit review --label Commit-Msg-Check='
        pass_cmd = f"{commom_cmd}+1 {self.args.account}"
        fail_cmd = f"{commom_cmd}-1 {self.args.account}"
        if headline and commit:
            check_output(pass_cmd, shell=True, stderr=STDOUT, text=True)
        elif not commit:
            check_output(fail_cmd, shell=True, stderr=STDOUT, text=True)
            exit(1)
        else:
            print("The commit message headline should in format: \
                   \n[<PRODUCT/TYPE> <version>] <Brief description>")
            check_output(fail_cmd, shell=True, stderr=STDOUT, text=True)
            exit(1)

    def get_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--commit-msg',
            type=str,
            dest="commit_msg",
            help="The gerrit commit message"
            )
        parser.add_argument(
            '--account',
            type=str,
            help="The account that used to change gerrit label"
            )
        parser.add_argument(
            '--prod-with-v',
            type=str,
            dest="prod_with_v",
            nargs='+',
            default=['CCDM', 'CCSM', 'CCRC', 'CCES', 'CCPC', 'PCC', 'PCG', 'SC', 'EDA'],
            help="The keyword list for product name that need version number"
            )
        parser.add_argument(
            '--type-without-v',
            type=str,
            dest="type_without_v",
            nargs='+',
            default=['JSONSCHEMA', 'UT', 'COMMON', 'StatusMatrix'],
            help="The keyword list for type name that needn't version number"
            )
        parser.add_argument(
            '--brief-start',
            type=str,
            dest="brief_start",
            nargs='+',
            default=['Initialize','Create','Update','Set','Apply','Modify', 'Introduce',
                     'Add','Remove','Delete','Adapt','Fix','Change','Align', 'Support',
                     'Correct','Optimize','Use','Merge','Simplify','Enable'],
            help="The keyword list for the beginning of brief description"
            )
        self.args = parser.parse_args()

    def check_headline(self):
        first_line = self.args.commit_msg.split('\n\n')[0]
        in_bracket = ''
        after_bracket = ''
        out = False
        format_revert = '''^Revert \\\\".*\\\\"'''
        format_msg = '^\[[a-zA-Z]+( [0-9]+\.[0-9]+)?\] [a-zA-Z]+.*'
        if re.match(format_revert, first_line):
            print('Pass for revert.')
            return True
        if '\n' in first_line:
            print("Invalid headline. Headline must be in single line and separated with paragraph with a blank line.")
            return False
        if not re.match(format_msg, first_line):
            print("Commit msg format error.")
            return False
        if len(first_line) > 70:
            print("Too long headline, the headline should no longer than 70 characters.")
            return False
        for i in range(1,len(first_line)):
            if not out:
                if first_line[i] == ']':
                    out = True
                else:
                    in_bracket += first_line[i]
            else:
                after_bracket += first_line[i]

        format_v = '^[0-9]+\.[0-9]+$'
        in_bracket = in_bracket.split()
        after_bracket = after_bracket.split()
        if after_bracket[0] in self.args.brief_start:
            if in_bracket[0] in self.args.type_without_v:
                if len(in_bracket)==1:
                    return True
                else:
                    print(f"For TYPE in {self.args.type_without_v}, the version number is not needed.")
                    return False
            elif in_bracket[0] in self.args.prod_with_v:
                if re.match(format_v,in_bracket[-1]):
                    return True
                else:
                    print(f"For PRODUCT in {self.args.prod_with_v}, the version number is necessary. \
                        \nThe version format should be like <integer>.<integer>")
                    return False
            else:
                print(f"The PRODUCT/TYPE in bracket should be in {self.args.prod_with_v} or {self.args.type_without_v}")
                return False
        else:
            print(f"The <Brief description> should start with {self.args.brief_start}.")
            return False

    def check_commit(self):
        print(f"Going to verify changed cnf and version.")
        git_cmd = "git log -1 --name-only | grep templates/"
        try:
            changed_files = check_output(git_cmd, shell=True, stderr=STDOUT, text=True).split('\n')
        except Exception as err:
            if not err.output.rstrip():
                changed_files = []
            else:
                raise Exception(f"{git_cmd} failed with: [{err.output.rstrip()}]")
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
            print(f"Commit change: {case_list}")
            return True
        else:
            error_msg = f""
            for cnf in case_list.keys():
                error_msg += f"CNF:{cnf} with version: {case_list[cnf]}\n"
            print(f"Only one version in one cnf should be changed in one commit.\n\
                    Following changes are made:\n{error_msg}")
            return False


if __name__ == '__main__':
    CheckCommitMsg().main()
