import secrets
class Config:
    """
    Set Flask configuration variables.
    """
    DOCKER_HOST:str = 'localhost:2376'
    CLOUDSHELL_PREFIX:str = 'cloudshell'
    SECRET_KEY_RANDOM:bool = True
    if SECRET_KEY_RANDOM:
        SECRET_KEY:str = secrets.token_hex(16)
    else:
        SECRET_KEY = 'What ever you want'