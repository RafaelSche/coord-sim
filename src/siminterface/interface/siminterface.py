# -*- coding: utf-8 -*-
"""
Module to abstract interaction between simulator and S&P
"""


class SimulatorAction:
    """
    Defines the actions to apply to the simulator environment.
    """

    def __init__(self,
                 placement,
                 scheduling):
        """initializes all properties since this is a data class

        Parameters
        ----------
        placement : dict
            {
                'node id' : [list of SF ids]
            }

        scheduling : dict
            {
                'node id' : dict
                {
                    'SFC id' : dict
                    {
                        'SF id' : dict
                        {
                            'node id : float
                        }
                    }
                }
            }

        Examples
        --------
        placement = {
            'pop0': ['a', 'c', 'd'],
            'pop1': ['b', 'c', 'd'],
            'pop2': ['a', 'b'],
        }
        schedule = {
            'pop0':
                 {'a': {'pop0': 0.4, 'pop1': 0.6, 'pop2': 0},
                  'b': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2},
                  'c': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2}},
            'pop1':
                 {'a': {'pop0': 0.3, 'pop1': 0.6, 'pop2': 0.1},
                  'b': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2},
                  'c': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2}},
            'pop2':
                 {'a': {'pop0': 0.1, 'pop1': 0.6, 'pop2': 0.3},
                  'b': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2},
                  'c': {'pop0': 0.6, 'pop1': 0.2, 'pop2': 0.2}}
        }

        action = SimulationActionInterface(placement, schedule)
        """
        self.placement = placement
        self.scheduling = scheduling


class SimulatorState:
    """
    Defines the state of the simulator environment.
    Contains all necessary information for an coordination algorithm.

    TODO: use integer for ids
    """
    def __init__(self,
                 network,
                 sfcs,
                 service_functions,
                 traffic,
                 network_stats):
        """initializes all properties since this is a data class

        Parameters
        ----------
        network : dict
            {
                'nodes': [{
                    'id': str,
                    'resource': [float],
                    'used_resources': [float]
                }],
                'edges': [{
                    'src': str,
                    'dst': str,
                    'delay': int (ms),
                    'data_rate': int (Mbit/s),
                    'used_data_rate': int (Mbit/s),
                }],
            }

        sfcs : list
            [{
                'id': str,
                'functions': list
                    ['ids (str)']
            }],

        service_functions : list
            [{
                'id': str,
                'processing_delay_mean': int (ms),
                'processing_delay_stdev': int (ms)
            }],


        << traffic: aggregated data rates of flows arriving at node requesting >>
        traffic : dict
            {
                'node_id (str)' : dict
                {
                    'sfc_id (str)': dict
                    {
                        'sf_id (str)': data_rate (int) [Mbit/s]
                    },
                },
            },

        network_stats : dict
            {
                'total_flows' : int,
                'successful_flows' : int,
                'dropped_flows' : int,
                'in_network_flows' : int
                'avg_end_2_end_delay' : int (ms)
            }
        """
        self.network = network
        self.sfcs = sfcs
        self.service_functions = service_functions
        self.traffic = traffic
        self.network_stats = network_stats


class SimulatorInterface:
    """
    Defines required method on the simulator object.
    """

    def init(self, network_file: str, service_functions_file: str, seed: int) -> SimulatorState:
        """Creates a new simulation environment.

        Parameters
        ----------
        network_file : str
            (Absolute) path to the network description.
        service_functions_file : str
            (Absolute) path to the service function description file.
        seed : int
            The seed value enables reproducible gym environments respectively
            reproducible simulator environments. This value should initialize
            the random number generator used by the simulator when executing
            randomized functions.

        Returns
        -------
        state: SimulationStateInterface
        """
        raise NotImplementedError

    def apply(self, actions: SimulatorAction) -> SimulatorState:
        """Applies set of actions.

        Parameters
        ----------
        actions: SimulationActionInterface

        Returns
        -------
        state: SimulationStateInterface
        """
        raise NotImplementedError
