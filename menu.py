#!/usr/bin/env python
# coding: utf-8

import sys, ConfigParser, requests, json, time, logging

class Parameters:

    def __init__(self, auth_config_file):
        self.current_config_file = None
        self.auth_config_file = auth_config_file
        self.auth_service_id = None
        self.auth_service_password = None
        self.auth_space = None

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
            print "Erreur de configuration dans le fichier %s : %s" % (self.current_config_file, e.message)
            sys.exit(1)

    def load_configs(self):
        self.parse_auth(self.auth_config_file)

class Api:

    BASE_URL = "https://www.dmc.sfr-sh.fr/DmcWS/1.5.1/JsonService"

    def __init__(self, parameters):
        self.parameters = parameters

    def create_authenticate_params(self, cur_params, space = False):
        cur_params["authenticate"] = {
            "serviceId": self.parameters.auth_service_id,
            "servicePassword": self.parameters.auth_service_password,
            "lang": "fr_FR"
        }
        if space:
            if self.parameters.auth_space is None:
                raise Exception("Aucun espace sélectionné, veuillez sélectionner un espace d'abord")
            cur_params["authenticate"]["spaceId"] = self.parameters.auth_space
        cur_params["authenticate"] = json.dumps(cur_params["authenticate"])

    def post(self, url, content):
        t0 = time.time()
        r = requests.post(url, data = content)
        t1 = time.time()
        print "Requête exécutée en %f secondes" % (t1-t0)
        try:
            j = json.loads(r.text)
            if not j["success"]:
                raise Exception("Erreur lors de la requête. Données retournées : %s" % j)
            return j
        except Exception, e:
            print e
            raise

    def findSpaces(self):
        p = {}
        self.create_authenticate_params(p)
        return self.post("%s/AdminWS/findSpaces" % Api.BASE_URL, p)

class Menu:

    def __init__(self, invite):
        self.menu_invite = invite

    def get_invite(self):
        return self.menu_invite

    def interact(self, content):
        s = None
        while True:
            print self.get_invite()
            for k, v in content.iteritems():
                print k, ".", v.get_invite()
            print "x", ".", "Retour"
            s = raw_input(">> ")
            if s == 'x':
                return
            elif s not in content.keys():
                continue
            else:
                content[s].run()

    def interactValue(self, content):
        s = None
        while True:
            print self.get_invite()
            for k, v in content.iteritems():
                print k, ".", v
            print "x", ".", "Retour"
            s = raw_input(">> ")
            print { "aze" : s }
            if s == 'x':
                return None
            elif s not in content.keys():
                continue
            else:
                return s

class SpaceMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, "Sélection des espaces")
        self.parameters = parameters
        self.spaces = None

    def get_space(self):
        s = Api(self.parameters).findSpaces()
        self.spaces = {}
        for v in s["response"]["list"]:
            self.spaces[str(v["spaceId"])] = "%s (%s)" % (
                v["spaceName"],
                "actif" if v["spaceActive"] else "inactif"
            )

    def run(self):
        if self.spaces is None:
            self.get_space()
        r = Menu.interactValue(self, self.spaces)
        self.parameters.auth_space = int(r)
        print "Espace sélectionné : %i" % self.parameters.auth_space

class MainMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, "Menu principal")
        self.parameters = parameters
        self.menus = {
            "1": SpaceMenu(self.parameters),
        }

    def run(self):
        Menu.interact(self, self.menus)

class App:

    AUTH_CONFIG_FILE = "auth.conf"

    def __init__(self):
        self.parameters = Parameters(App.AUTH_CONFIG_FILE)
        self.parameters.load_configs()
        self.main_menu = MainMenu(self.parameters)

    def setup_logging(self):
        logging.basicConfig()
        if len(sys.argv) != 2 or sys.argv[1] != "--debug":
            return
        try:
            import http.client as http_client
        except ImportError:
            import httplib as http_client
            logging.getLogger().setLevel(logging.DEBUG)
        http_client.HTTPConnection.debuglevel = 1
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    def run(self):
        self.setup_logging()
        self.main_menu.run()

if __name__ == "__main__":
    app = App()
    app.run()
