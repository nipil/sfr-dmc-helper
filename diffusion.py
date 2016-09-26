#!/usr/bin/env python
# coding: utf-8

import sys, ConfigParser, requests, json, time, logging, re, argparse

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

    def create_broadcast_id_param(self, cur_params):
        cur_params["broadcastId"] = str(self.parameters.broadcast_id)

    def create_add_contact_params(self, cur_params):
        self.create_broadcast_id_param(cur_params)
        cur_params["contact"] = [{
            "phoneNumber1": self.parameters.phone_number,
        }]
        cur_params["contact"] = json.dumps(cur_params["contact"])

    def post(self, url, content, info=True):
        logging.debug("Requests arguments : %s", content)
        t0 = time.time()
        r = requests.post(url, data = content)
        t1 = time.time()
        logging.debug("Requests duration : %s", t1 - t0)
        t = r.text
        logging.debug("Requests Reply : %s", t)
        j = json.loads(t)
        if not j["success"]:
            raise Exception("Erreur lors de la requête. Données retournées : %s" % j)
        return j

    def findSpaces(self):
        logging.info("Récupération des espaces")
        p = {}
        self.create_authenticate_params(p, False)
        return self.post("%s/AdminWS/findSpaces" % Api.BASE_URL, p)

    def findPlanning(self):
        logging.info("Récupération des plannings")
        p = {}
        self.create_authenticate_params(p)
        return self.post("%s/PlanningWS/findPlanning" % Api.BASE_URL, p)

    def findScenarii(self):
        logging.info("Récupération des scenarii")
        p = {}
        self.create_authenticate_params(p)
        return self.post("%s/BroadcastWS/findScenarii" % Api.BASE_URL, p)

    def createBroadcast(self):
        logging.info("Création d'une diffusion")
        p = {}
        self.create_authenticate_params(p)
        self.create_broadcast_params(p)
        return self.post("%s/BroadcastWS/createBroadcast" % Api.BASE_URL, p)

    def addContactToBroadcast(self):
        logging.info("Ajout du contact à la diffusion")
        p = {}
        self.create_authenticate_params(p)
        self.create_add_contact_params(p)
        return self.post("%s/BroadcastWS/addContactToBroadcast" % Api.BASE_URL, p)

    def getBroadcast(self, info=True):
        logging.info("Récupération des informations de la diffusion")
        p = {}
        self.create_authenticate_params(p)
        self.create_broadcast_id_param(p)
        return self.post("%s/BroadcastWS/getBroadcast" % Api.BASE_URL, p, info)

    def findBroadcastCra(self, info=True):
        logging.info("Récupération du compte rendu d'appel de la diffusion")
        p = {}
        self.create_authenticate_params(p)
        self.create_broadcast_id_param(p)
        return self.post("%s/SupervisionWS/findBroadcastCra" % Api.BASE_URL, p, info)

    def activateBroadcast(self):
        logging.info("Activation de la diffusion")
        p = {}
        self.create_authenticate_params(p)
        self.create_broadcast_id_param(p)
        return self.post("%s/BroadcastWS/activateBroadcast" % Api.BASE_URL, p)

    def dropBroadcast(self):
        logging.info("Suppression de la diffusion")
        p = {}
        self.create_authenticate_params(p)
        self.create_broadcast_id_param(p)
        return self.post("%s/BroadcastWS/dropBroadcast" % Api.BASE_URL, p)

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
            raise Exception("Numéro de téléphone invalide, utiliser le format international")
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

    def dropBroadcast(self):
        r = Api(self.parameters).dropBroadcast()
        if r["success"]:
            print "Diffusion %s supprimée" % self.parameters.broadcast_id
        else:
            print "Erreur: %s" % r["errorDetail"]

    def createBroadcast(self):
        r = Api(self.parameters).createBroadcast()
        self.parameters.broadcast_id = r["response"]["broadcastId"]
        print "Diffusion %s créée" % self.parameters.broadcast_id

    def addContactToBroadcast(self):
        r = Api(self.parameters).addContactToBroadcast()
        if not r["response"][0]["saved"]:
            raise Exception(r["response"][0]["error"])
        else:
            print "Contact ajouté (id %s)" % r["response"][0]["contactId"]

    def activateBroadcast(self):
        r = Api(self.parameters).activateBroadcast()
        return r

    def getBroadcastStatus(self):
        r = Api(self.parameters).getBroadcast(False)
        return r

    def getBroadcastCra(self):
        r = Api(self.parameters).findBroadcastCra(False)
        return r

    def waitForBroadcastCompletion(self):
        last_status_code = None
        last_cra = None
        while True:
            status = self.getBroadcastStatus()
            if status != last_status_code:
                print "Etat de la diffusion : %s" % status["response"]["statusCode"]
                last_status_code = status
            cra = self.getBroadcastCra()
            if cra != last_cra:
                l = cra["response"]["list"][0]
                print "CRA actuel : %s (%s)" % (l["callResult"], l["callResultCode"])
                last_cra = cra
            if status == "BR_FINISHED":
                break
            time.sleep(1)

    def run(self):
        if self.parameters.broadcast_id is None:
            self.createBroadcast()
        self.addContactToBroadcast()
        self.activateBroadcast()
        self.waitForBroadcastCompletion()
        cra = self.getBroadcastCra()
        l = cra["response"]["list"][0]
        print "CRA final : %s (%s)" % (l["callResult"], l["callResultCode"])
        if self.parameters.broadcast_id is not None:
            self.dropBroadcast()
            self.parameters.broadcast_id = None

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
        self.arguments = None

    def setup_logging(self):
        numeric_level = getattr(logging, self.arguments.log.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Niveau de log invalide: %s' % loglevel)
        logging.basicConfig(level=numeric_level, format='%(asctime)s %(name)s %(levelname)s %(message)s')
        # try:
        #     import http.client as http_client
        # except ImportError:
        #     import httplib as http_client
        #     logging.getLogger().setLevel(logging.DEBUG)
        # http_client.HTTPConnection.debuglevel = 1
        # requests_log = logging.getLogger("requests.packages.urllib3")
        # requests_log.setLevel(numeric_level)
        # requests_log.propagate = True

    def parse_arguments(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--menu', action='store_true', help='affiche les menus interactifs')
        parser.add_argument('--log', help='choix du niveau de log', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'EXCEPTION'], default='WARNING')
        self.arguments = parser.parse_args()

    def run(self):
        self.parse_arguments()
        self.setup_logging()
        if self.arguments.menu :
            self.main_menu.run()

if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except KeyboardInterrupt:
        pass
