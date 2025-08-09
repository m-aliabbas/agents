import yaml
import requests

from config import SERVER_URI
def load_yaml(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)


def load_instructions(file_path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        print(e)
        return "You are friendly assistant. You can ask me anything."
    

def get_agent_from_web(agent_id: str):
    """
    Fetch agent details from the API.
    
    Args:
        agent_id (str): The UUID of the agent.

    Returns:
        dict: Agent data if found, else None.
    """
    BASE_URL = f"{SERVER_URI}/agent"
    url = f"{BASE_URL}/{agent_id}"
    headers = {"accept": "application/json"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise error if status != 200
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - {response.text}")
    except Exception as err:
        print(f"Other error occurred: {err}")
    return None

    