#!/usr/bin/env python

import sys, ConfigParser

class Parameters:

    def __init__(self, auth_config_file):
        self.current_config_file = None
        self.auth_config_file = auth_config_file
        self.auth_service_id = None
        self.auth_service_password = None

    def load_config(self, file):
        self.current_config_file = file
        config = ConfigParser.RawConfigParser()
        config.read(file)
        return config

    def parse_auth(self, file):
        config = self.load_config(file)
        self.auth_service_id = self.get_section_param(config, "authentication", "serviceId")
        self.auth_service_password = self.get_section_param(config, "authentication", "servicePassword")

    def get_section_param(self, config, section, param):
        try:
            return config.get(section, param)
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as e:
            print "Erreur de configuration dans le fichier " + self.current_config_file + " : " + e.message
            raise
            sys.exit(1)

    def load_configs(self):
        self.parse_auth(self.auth_config_file)


class App:

    AUTH_CONFIG_FILE = "auth.conf"

    def __init__(self):
        self.parameters = Parameters(App.AUTH_CONFIG_FILE)
        self.parameters.load_configs()

    def run(self):
        pass

if __name__ == "__main__":
    app = App()
    app.run()
