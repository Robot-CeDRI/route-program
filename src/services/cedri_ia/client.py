import httpx
from config import settings
from core import messages as m
from core.log import log

LOAD_ENDPOINT       = "/api/models/load"
UNLOAD_ENDPOINT     = "/api/models/unload"
CREATE_ENDPOINT     = "/api/models/create"
PROCESS_ENDPOINT    = "/api/models/process"
TRAIN_ENDPOINT      = "/api/models/train"
CHECK_ENDPOINT      = "/api/models/check"
HELLO_ENDPOINT      = "/api/echo"

class CEDRIClient:
    """
    A unified client for interacting with the CEDRI IA Manager REST API.
    """
    def __init__(self):
        self.ip = settings[m.IPIA]
        self.port = settings[m.PORTIA]
        self.base_url = f"http://{self.ip}:{self.port}"

        self.hello_timeout = float(settings[m.HELLO_TIMEOUT])
        self.default_timeout = float(settings[m.DEFAUT_TIMEOUT])

    def _make_request(self, method: str, endpoint: str, payload: dict = None, timeout: float = None) -> dict:
        """
        Internal helper method to handle HTTP requests and standardize error logging.
        """
        url = f"{self.base_url}{endpoint}"
        req_timeout = timeout if timeout is not None else self.default_timeout
        
        log(f"[{method}] Requesting IA Manager: {url}")
        
        try:
            if method.upper() == "GET":
                response = httpx.get(url, timeout=req_timeout)
            elif method.upper() == "POST":
                response = httpx.post(url, timeout=req_timeout, json=payload)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            
            return response.json()

        except httpx.HTTPStatusError as exc:
            log(f"HTTP error on IA (Status {exc.response.status_code}) on solicitation {exc.request.url}.", 2)
            return {"error": True, "status_code": exc.response.status_code, "detail": str(exc)}
        except httpx.RequestError as exc:
            log(f"Failure {exc.request.url}. Is the IA Manager turned on?", 3)
            return {"error": True, "detail": "Connection Failed"}
        except Exception as e:
            log(f"Unexpected error calling {url}: {e}", 3)
            return {"error": True, "detail": str(e)}

    # ==========================================
    #       IA OPERATIONS
    # ==========================================

    def hello(self) -> bool:
        """Pings the IA Manager to check if it's online."""
        response = self._make_request("GET", HELLO_ENDPOINT, timeout=self.hello_timeout)
        if response and not response.get("error"):
            log(f"Success! IA Manager responded: {response}")
            return True
        return False

    def check_model(self, payload: dict) -> dict:
        """Checks the status or details of a model."""
        return self._make_request("POST", CHECK_ENDPOINT, payload=payload)

    def create_model(self, payload: dict) -> dict:
        """Creates a new model in the IA Manager."""
        return self._make_request("POST", CREATE_ENDPOINT, payload=payload)

    def load_model(self, payload: dict) -> dict:
        """Loads a model into memory."""
        return self._make_request("POST", LOAD_ENDPOINT, payload=payload)

    def process_data(self, payload: dict) -> dict:
        """Sends data to a loaded model for processing/inference."""
        return self._make_request("POST", PROCESS_ENDPOINT, payload=payload)

    def train_model(self, payload: dict) -> dict:
        """Initiates the training process for a model."""
        return self._make_request("POST", TRAIN_ENDPOINT, payload=payload)

    def unload_model(self, payload: dict) -> dict:
        """Unloads a model from memory."""
        return self._make_request("POST", UNLOAD_ENDPOINT, payload=payload)

ia_client = CEDRIClient()