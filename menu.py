#!/usr/bin/env python
# coding: utf-8

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


class SpaceMenu:

    def __init__(self, parameters):
        self.parameters = parameters

    def get_invite(self):
        return "Sélection des espaces"

    def run(self):
        print "space menu"
        pass

class MainMenu:

    def __init__(self, parameters):
        self.parameters = parameters
        self.menus = {
            "1": SpaceMenu(self.parameters),
        }

    def get_invite(self):
        return "Menu principal"

    def run(self):
        s = None
        while True:
            print self.get_invite()
            for k, v in self.menus.iteritems():
                print k + ".", v.get_invite()
            print "x. Retour"
            s = raw_input(" >> ")
            if s == 'x':
                return
            elif s not in self.menus.keys():
                continue
            else:
                self.menus[s].run()

class App:

    AUTH_CONFIG_FILE = "auth.conf"

    def __init__(self):
        self.parameters = Parameters(App.AUTH_CONFIG_FILE)
        self.parameters.load_configs()
        self.main_menu = MainMenu(self.parameters)

    def run(self):
        self.main_menu.run()

if __name__ == "__main__":
    app = App()
    app.run()
