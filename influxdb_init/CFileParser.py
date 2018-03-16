#!/bin/env python3
#
# Config File Parser
# uses PyYAML
# 

# basig library import
import yaml
try:
    from yaml import CLoader
except ImportError:
    print("CLoader not found in yaml module.")
    raise ImportError

# config wrapper class
class CFileParser():
    # constructor, loads config file in yaml form
    def __init__(self, filename):
        # load config parameters from file
        try:
            with open(filename, 'r') as input_stream:
                self.config_repr = yaml.load(input_stream)
        except IOError as e:
            raise e
        except FileNotFoundError as e:
            raise e
        except:
            raise

    def parse(self):
        # dynamically add fields and methods
        for robj in self.config_repr.keys():
            method_implementation = self.config_repr[robj]
            setattr(self.__class__, robj, method_implementation)

##

