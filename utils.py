def config_parser(config_path):
    with open(config_path) as config_file:
        config = dict()
        for line in config_file:
            k,v = line.split(' = ')
            config[k] = v.split('\n')[0]
        return config
