import random
import logging
import string
import numpy as np
# from coordsim.reader import networkreader
from coordsim.network.flow import Flow
from coordsim.network import scheduler
log = logging.getLogger(__name__)


# Generate flows at the ingress nodes.
def generate_flow(env, node_id, sf_placement, sfc_list, sf_list, inter_arr_mean, network,
                  flow_dr_mean, flow_dr_stdev, flow_size_shape, vnf_delay_mean, vnf_delay_stdev):
    # log.info flow arrivals, departures and waiting for flow to end (flow_duration) at a pre-specified rate
    while True:
        flow_id = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(6))
        flow_id_str = "{}-{}".format(node_id, flow_id)
        # Exponentially distributed random inter arrival rate using a user set (or default) mean
        inter_arr_time = random.expovariate(inter_arr_mean)
        # Assign a random flow datarate and size according to a normal distribution with config. mean and stdev.
        # Abs here is necessary as normal dist. gives negative numbers.
        flow_dr = np.absolute(np.random.normal(flow_dr_mean, flow_dr_stdev))
        # Use a Pareto distribution (Heavy tail) random variable to generate flow sizes
        flow_size = np.absolute(np.random.pareto(flow_size_shape)) + 1
        # Normal Dist. may produce zeros. That is not desired. We skip the remainder of the loop.
        if flow_dr == 0 or flow_size == 0:
            continue
        flow_sfc = np.random.choice([sfc for sfc in sfc_list.keys()])
        # Generate flow based on given params
        flow = Flow(flow_id_str, flow_sfc, flow_dr, flow_size, current_node_id=node_id)
        # Generate flows and schedule them at ingress node
        env.process(schedule_flow(env, node_id, flow, sf_placement, sfc_list, sf_list, network, vnf_delay_mean,
                    vnf_delay_stdev))
        yield env.timeout(inter_arr_time)


# Filter out non-ingree nodes.
def ingress_nodes(network):
    ing_nodes = []
    for node in network.nodes.items():
        if node[1]["type"] == "Ingress":
            ing_nodes.append(node)
    return ing_nodes


# Process the flow at the requested SF of the current node.
def process_flow(env, node_id, flow):
    log.info(
        "Flow {} processed by sf '{}' at node {}. Time {}"
        .format(flow.flow_id, flow.current_sf, node_id, env.now))


# When the flow is in the last SF of the requested SFC. Depart it from the network.
def flow_departure(env, node_id, flow):
    log.info("Flow {} was fully processed and departed network from {}. Time {}".format(flow.flow_id, node_id, env.now))


# Determine whether flow stays in the same node. Otherwise forward flow and log the action taken.
def flow_forward(env, node_id, next_node, flow):
    if(node_id == next_node):
        log.info("Flow {} stays in node {}. Time: {}.".format(flow.flow_id, flow.current_node_id, env.now))
    else:
        log.info("Flow {} departed node {} to node {}. Time {}"
                 .format(flow.flow_id, flow.current_node_id, next_node, env.now))
        flow.current_node_id = next_node


# Schedule flows. This function takes the generated flow object at the ingress node and handles it according
# to the requested SFC. We check if the SFC that is being requested is indeed within the schedule, otherwise
# we log a warning and drop the flow.
# The algorithm will check the flow's requested SFC, and will forward the flow through the network using the
# SFC's list of SFs based on the LB rules that are provided through the scheduler's 'flow_schedule()'
# function.
def schedule_flow(env, node_id, flow, sf_placement, sfc_list, sf_list, network, vnf_delay_mean, vnf_delay_stdev):
    log.info(
        "Flow {} generated. arrived at node {} Requesting {} - flow duration: {}. Time: {}"
        .format(flow.flow_id, node_id, flow.sfc, flow.duration, env.now))
    schedule = scheduler.flow_schedule()
    sfc = sfc_list.get(flow.sfc, None)
    if sfc is not None:
        for index, sf in enumerate(sfc_list[flow.sfc]):
            schedule_sf = schedule[flow.current_node_id][sf]
            flow.current_sf = sf
            sf_nodes = [sch_sf for sch_sf in schedule_sf.keys()]
            sf_probability = [prob for name, prob in schedule_sf.items()]
            next_node = np.random.choice(sf_nodes, 1, sf_probability)[0]
            if sf in sf_placement[next_node]:
                flow_forward(env, flow.current_node_id, next_node, flow)
                # Get node capacity and remaining capacity from NetworkX graph
                node_cap = network.nodes[flow.current_node_id]["cap"]
                node_remaining_cap = network.nodes[flow.current_node_id]["remaining_cap"]
                assert node_remaining_cap >= 0, "Remaining node capacity cannot be less than 0 (zero)!"
                # Check if the flow's dr is less or equals the node's remaining capacity, then process the flow.
                if flow.dr <= node_remaining_cap:
                    node_remaining_cap -= flow.dr
                    processing_delay = np.absolute(np.random.normal(vnf_delay_mean, vnf_delay_stdev))
                    yield env.timeout(processing_delay + flow.duration)
                    process_flow(env, flow.current_node_id, flow)
                    node_remaining_cap += flow.dr
                    # We assert that remaining capacity must at all times be less than the node capacity so that
                    # nodes dont put back more capacity than the node's capacity.
                    assert node_remaining_cap <= node_cap, "Node remaining capacity cannot be more than node capacity!"
                # If there is not enough capacity, then drop flow by breaking the SFC loop.
                # This is the best place to place this check as it checks each node without modifying much of the code
                else:
                    log.info("Not enough capacity for flow {} at node {}. Dropping flow.".format(flow.flow_id,
                             flow.current_node_id))
                    break
                if(index == len(sfc_list[flow.sfc])-1):
                    flow_departure(env, flow.current_node_id, flow)
            else:
                log.warning("SF was not found at requested node. Dropping flow {}".format(flow.flow_id))
    else:
        log.warning("No Scheduling rule for requested SFC. Dropping flow {}".format(flow.flow_id))


# Start the simulator.
def start_simulation(env, network, sf_placement, sfc_list, sf_list, inter_arr_mean=1.0, flow_dr_mean=1.0,
                     flow_dr_stdev=1.0, flow_size_shape=1.0, vnf_delay_mean=1.0,
                     vnf_delay_stdev=1.0):
    log.info("Starting simulation")
    nodes_list = [n[0] for n in network.nodes.items()]
    log.info("Using nodes list {}\n".format(nodes_list))
    ing_nodes = ingress_nodes(network)
    log.info("Total of {} ingress nodes available\n".format(len(ing_nodes)))
    for node in ing_nodes:
        node_id = node[0]
        env.process(generate_flow(env, node_id, sf_placement, sfc_list, sf_list, inter_arr_mean, network,
                                  flow_dr_mean, flow_dr_stdev, flow_size_shape, vnf_delay_mean, vnf_delay_stdev))
