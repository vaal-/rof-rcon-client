RCon client for ROF dserver
===============

Usage
-----

    $ pip install rof-rcon-client

Example

login, password, host, port from startup.cfg: account|login, account|password, system|rcon_ip, system|rcon_port

    import logging
    from rof_rcon_client import RConClient
    
    logging.basicConfig(level=logging.DEBUG)
    rcon = RConClient(login='login', password='password', host='ip', port=8991)
    print(rcon.get_sps())
