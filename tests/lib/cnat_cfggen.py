from .common import dump_yaml_file, load_yaml_file, run_cmd


class CfgGen(object):
    """cfggen Class"""
    def __init__(self, cfggen_info_file, templates_dir, cnat_path, output_dir):
        self.cfggen_info_file = cfggen_info_file
        self.templates_dir = templates_dir
        self.cnat_path = cnat_path
        self.output_dir = output_dir

    def generate_config(self):
        """Generate the config files by CNAT"""
        cfggen_info_file = self.cfggen_info_file.split('/')
        cfggen_info_file[-1] = f'copy_{cfggen_info_file[-1]}'
        cfggen_info_file = '/'.join(cfggen_info_file)
        # rewrite 'templateDir' and 'targetDir'
        content = load_yaml_file(self.cfggen_info_file)
        content['templateDir'] = self.templates_dir
        content['targetDir'] = self.output_dir
        dump_yaml_file(content, cfggen_info_file)
        # run CNAT command
        cmd = f"{self.cnat_path} -g --cfggen-info {cfggen_info_file}"
        result = run_cmd(cmd)
        return result
