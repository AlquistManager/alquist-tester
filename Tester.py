import json
import re
import threading
from random import randint

import requests


class Tester(threading.Thread):
    def __init__(self, url, loaded_yaml, name):
        threading.Thread.__init__(self)
        self.context = {}
        self.state = "init"
        self.session = ""
        self.response_text = ""
        self.isUserTurn = True
        self.url = url
        self.loaded_yaml = loaded_yaml
        self.name = name

    def run(self):
        if self.execute_test(self.loaded_yaml):
            print(self.name + ": Dialogue ended successfully.")

    # sends post to Alquist and return its response
    def send_post(self, url, text, context, state, session):
        payload = {'text': text, 'context': context, 'state': state, 'session': session}
        headers = {'content-type': 'application/json'}
        return requests.post(url, data=json.dumps(payload), headers=headers)

    # tests dialogue
    def execute_test(self, loaded_yaml):
        i = 0
        # while we are not at the end of yaml
        while i < len(loaded_yaml):
            # if it is user's turn
            if loaded_yaml[i]["agent"] == "user":
                # select one input at random
                randomly_selected = self.select_random_input(loaded_yaml[i]["input"])
                # take text and transition
                text_to_send = randomly_selected["text"]
                print(self.name + ": "+
                text_to_send)
                # take transition, if presented
                if 'transition' in randomly_selected:
                    i = randomly_selected["transition"] - 1
                # send it to Alquist
                response = self.send_post(self.url, text_to_send, self.context, self.state, self.session)
                # save info from response
                self.save_info_from_response(response)
                print(self.name + ": " + response.json()["text"])
                self.isUserTurn = False
            # if it is Alquist's turn
            elif loaded_yaml[i]["agent"] == "alquist":
                if self.isUserTurn:
                    response = self.send_post(self.url, "", self.context, self.state, self.session)
                    # save info from response
                    self.save_info_from_response(response)
                    print(self.name + ": " + response.json()["text"])
                # check last response
                if not (self.test_response_test(self.response_text, loaded_yaml[i]["output"])):
                    # we founded mistake
                    print(
                        self.name + ': There is mistake in the state ' + self.state + '. Response text "' + self.response_text + '" was unexpected.')
                    return False
                # if we have transition field
                if 'transition' in loaded_yaml[i]:
                    # if there is return in transition field, then return successfully
                    if loaded_yaml[i]['transition'] == "return":
                        return True
                    else:
                        # otherwise where we have to
                        i = loaded_yaml[i]["transition"] - 1
                self.isUserTurn = True
            i += 1
        return True

    # save context, state, session and response from Alquist's request
    def save_info_from_response(self, response):
        self.context = response.json()['context']
        self.state = response.json()['state']
        self.session = response.json()['session']
        self.response_text = response.json()['text']

    # select one input at random
    def select_random_input(self, inputs):
        index = randint(0, len(inputs) - 1)
        return inputs[index]

    # test if response is the same as any possible response
    def test_response_test(self, response_text, text_from_yaml):
        # test all responses
        for text in text_from_yaml:
            if self.test_response_test_all_variants(response_text, text):
                return True
        return False

    # change substitute {{possibility1, possibility2}} to possibility1 and possibility2 in possible output
    def test_response_test_all_variants(self, response_text, text_from_yaml):
        # search for {{ pattern }}
        m = re.search('(?<={{)(.*?)(?=}})', text_from_yaml)
        if m:
            variants = m.group(1)
            # split inside of pattern
            variants = variants.split(",")
            # substitute pattern
            for variant in variants:
                text = re.sub('({{)(.*?)(}})', variant, text_from_yaml)
                if text == response_text:
                    return True
                return False
        # no pattern founded
        elif response_text == text_from_yaml:
            return True
        return False
