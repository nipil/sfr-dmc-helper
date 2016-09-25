#!/usr/bin/env python
# coding: utf-8

import sys, ConfigParser, requests, json, time, logging, re

class Parameters:

    def __init__(self, auth_config_file):
        self.current_config_file = None
        self.auth_config_file = auth_config_file
        # auth.conf
        self.auth_service_id = None
        self.auth_service_password = None
        # space menu
        self.auth_space = None
        # planning menu
        self.planning_id = None
        # scenario menu
        self.scenario_id = None
        # phone menu
        self.phone_number = None
        # broadcast menu
        self.broadcast_id = None

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

    def create_authenticate_params(self, cur_params, space = True):
        cur_params["authenticate"] = {
            "serviceId": str(self.parameters.auth_service_id),
            "servicePassword": str(self.parameters.auth_service_password),
            "lang": "fr_FR"
        }
        if space:
            if self.parameters.auth_space is None:
                raise Exception("Aucun espace sélectionné, veuillez sélectionner un espace d'abord")
            cur_params["authenticate"]["spaceId"] = str(self.parameters.auth_space["id"])
        cur_params["authenticate"] = json.dumps(cur_params["authenticate"])

    def create_broadcast_params(self, cur_params):
        cur_params["broadcast"] = {
            "callPlanningId": str(self.parameters.planning_id["id"]),
            "scenarioId": str(self.parameters.scenario_id["id"]),
            "broadcastName": "python helper diffusion %s" % time.strftime("%Y-%m-%d@%H:%M:%S")
        }
        cur_params["broadcast"] = json.dumps(cur_params["broadcast"])

    def post(self, url, content):
        t0 = time.time()
        r = requests.post(url, data = content)
        t1 = time.time()
        print "Requête exécutée en %f secondes" % (t1-t0)
        j = json.loads(r.text)
        if not j["success"]:
            raise Exception("Erreur lors de la requête. Données retournées : %s" % j)
        return j

    def findSpaces(self):
        print "Récupération des espaces"
        p = {}
        self.create_authenticate_params(p, False)
        return self.post("%s/AdminWS/findSpaces" % Api.BASE_URL, p)

    def findPlanning(self):
        print "Récupération des plannings"
        p = {}
        self.create_authenticate_params(p)
        return self.post("%s/PlanningWS/findPlanning" % Api.BASE_URL, p)

    def findScenarii(self):
        print "Récupération des scenarii"
        p = {}
        self.create_authenticate_params(p)
        return self.post("%s/BroadcastWS/findScenarii" % Api.BASE_URL, p)

    def createBroadcast(self):
        print "Création d'une diffusion"
        p = {}
        self.create_authenticate_params(p)
        self.create_broadcast_params(p)
        return self.post("%s/BroadcastWS/createBroadcast" % Api.BASE_URL, p)

class Menu:

    def __init__(self, parameters, invite):
        self.parameters = parameters
        self.menu_invite = invite

    def get_invite(self):
        return self.menu_invite

    def is_valid(self):
        return True

    def id_desc_to_str(self, v):
        if v is None:
            return None
        return "%s %s" % (v["id"], v["desc"])

    def interact(self, content):
        s = None
        while True:
            print "=" * 70
            print "Espace : %s" % self.id_desc_to_str(self.parameters.auth_space)
            print "Planning : %s" % self.id_desc_to_str(self.parameters.planning_id)
            print u"Scénario : %s" % self.id_desc_to_str(self.parameters.scenario_id)
            print "Numéro : %s" % self.parameters.phone_number
            print "-" * 70
            print self.get_invite()
            for k, v in enumerate(content):
                if not v.is_valid():
                    continue
                print k, ".", v.get_invite()
            print "q", ".", "Quitter"
            s = raw_input(">> ")
            if s == 'q' or s == '':
                return
            s = int(s)
            if s < 0 or s >= len(content):
                continue
            else:
                try:
                    content[s].run()
                except Exception, e:
                    print "ERREUR: %s" % e.message
                    s = None

    def interactValue(self, content):
        s = None
        while True:
            print "=" * 70
            print self.get_invite()
            for k, v in content.iteritems():
                print k, ".", v
            s = raw_input(">> ")
            if s not in content.keys():
                continue
            else:
                return s

class SpaceMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, parameters, "Sélection des espaces")
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
        self.parameters.auth_space = { "id": int(r), "desc": self.spaces[r] }
        print "Espace sélectionné : %i" % self.parameters.auth_space["id"]

class PlanningMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, parameters, "Sélection du planning")
        self.plannings = None

    def is_valid(self):
        return self.parameters.auth_space is not None

    def get_planning(self):
        s = Api(self.parameters).findPlanning()
        self.plannings = {}
        for v in s["response"]:
            self.plannings[str(v["planningId"])] = v["planningName"]

    def run(self):
        if self.plannings is None:
            self.get_planning()
        r = Menu.interactValue(self, self.plannings)
        self.parameters.planning_id = { "id": int(r), "desc": self.plannings[r] }
        print "Planning sélectionné : %i" % self.parameters.planning_id["id"]

class ScenarioMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, parameters, "Sélection du scénario")
        self.scenarios = None

    def is_valid(self):
        return self.parameters.auth_space is not None

    def get_scenario(self):
        s = Api(self.parameters).findScenarii()
        self.scenarios = {}
        r = re.compile(r"^is")
        for v in s["response"]:
            self.scenarios[str(v["scenarioId"])] = "%s (%s)" % (
                v["scenarioName"],
                ', '.join([ r.sub("", k) for k in ['isMms', 'isVocal', 'isEmail', 'isFax', 'isSms'] if v[k] ])
            )

    def run(self):
        if self.scenarios is None:
            self.get_scenario()
        r = Menu.interactValue(self, self.scenarios)
        self.parameters.scenario_id = { "id": int(r), "desc": self.scenarios[r] }
        print "Scénario sélectionné : %i" % self.parameters.scenario_id["id"]

class PhoneMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, parameters, "Sélection du numéro (+33xxxxxxxxx)")
        self.numero = None

    def is_valid(self):
        return True

    def run(self):
        r = re.compile(r"\+33\d{7}")
        while True:
            print "=" * 70
            print self.get_invite()
            s = raw_input(">> ")
            if r.match(s):
                break
            print "Numéro de téléphone invalide, utiliser le format international"
        self.parameters.phone_number = s
        print "Numéro sélectionné : %s" % self.parameters.phone_number

class BroadcastMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, parameters, "Lancement de la diffusion")

    def is_valid(self):
        return (
            self.parameters.auth_space is not None and
            self.parameters.planning_id is not None and
            self.parameters.scenario_id is not None and
            self.parameters.phone_number is not None
        )

    def createBroadcast(self):
        r = Api(self.parameters).createBroadcast()
        self.parameters.broadcast_id = r["response"]["broadcastId"]

    def run(self):
        if self.parameters.broadcast_id is None:
            self.createBroadcast()

class MainMenu(Menu):

    def __init__(self, parameters):
        Menu.__init__(self, parameters, "Menu principal")
        self.menus = [
            SpaceMenu(self.parameters),
            PlanningMenu(self.parameters),
            ScenarioMenu(self.parameters),
            PhoneMenu(self.parameters),
            BroadcastMenu(self.parameters),
        ]

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
    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        pass
