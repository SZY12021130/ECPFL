def num_client():
    return 50

def sys_mode():
    return true

def nb_round():
    return 50

def get_slot_size():
    log_slots = 13
    return 2**log_slots

def get_cudaid():
    cuda_id = "cuda:0"
    return cuda_id

def get_masking_threshold():
    threshold = 90
    return threshold

def get_masking_type():
    masking_type = "maser"
    return masking_type

def get_model_name():
    model_name = "lenet"
    return model_name

def get_dataset_name():
    dataset_name = "mnist"
    return dataset_name

def get_distribution_type():
    distribution_type = "non_iid"
    return distribution_type

def get_alpha_value():
    alpha = float(1.0)
    return alpha

def get_server_addr():
    ip = "127.0.0.1"
    port = 6003
    return ip, port

def get_key_manager_addr():
    ip = "127.0.0.1"
    port_key_send = 6000
    port_key_recv = 6001
    return ip, port_key_send, port_key_recv

def get_localhost():
    ip = "0.0.0.0"
    return ip

def get_local_ep():
    return 1

def get_local_lr():
    return 1e-3

def get_mu_value():
    mu = 1.0
    return mu
