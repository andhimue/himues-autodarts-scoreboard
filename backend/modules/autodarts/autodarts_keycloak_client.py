from datetime import datetime, timedelta
from keycloak import KeycloakOpenID
import gevent
from ..core import shared_state as g

class AutodartsKeycloakClient:
    token_lifetime_fraction = 0.75
    tick: int = 3
    run: bool = True
    username: str = None
    password: str = None
    debug: bool = False
    kc: KeycloakOpenID = None
    access_token: str = None
    refresh_token: str = None
    user_id: str = None
    expires_at: datetime = None
    renewal_threshold: datetime = None
    
    t: gevent.Greenlet = None

    def __init__(self, *, username: str, password: str, client_id: str, client_secret: str = None, debug: bool = False):
        self.kc = KeycloakOpenID(
            server_url="https://login.autodarts.io",
            client_id=client_id,
            client_secret_key=client_secret,
            realm_name="autodarts",
            verify=True
        )
        self.username = username
        self.password = password
        self.debug = debug
        self.__get_token()
        self.user_id = self.kc.userinfo(self.access_token)['sub']

    def __set_token(self, token: dict):
        self.access_token = token.get('access_token')
        # Der Refresh-Token wird nur aktualisiert, wenn er in der Antwort enthalten ist
        # Er wird vom Autodarts-Server mit einer LAufzeit von 0 gemeldet, ist also dauerhaft gültg
#        if token.get('refresh_token'):
        self.refresh_token = token.get('refresh_token')
        
        self.expires_at = datetime.now() + timedelta(seconds=token.get("expires_in", 0))
        self.renewal_threshold = datetime.now() + timedelta(
            seconds=int(self.token_lifetime_fraction * token.get("expires_in", 0))
        )

    def __get_token(self):
        self.__set_token(self.kc.token(self.username, self.password))
        if self.debug:
            print("Getting initial token")

    def __refresh_token(self):
        self.__set_token(self.kc.refresh_token(self.refresh_token))
        if self.debug:
            print("Refreshing access token")
            
    def __format_timedelta(self, td):
        """Formatiert ein timedelta-Objekt in einen lesbaren String."""
        days = td.days
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if days > 0: return f"{days}d {hours}h"
        if hours > 0: return f"{hours}h {minutes}m"
        if minutes > 0: return f"{minutes}m {seconds}s"
        return f"{seconds}s"

    def __get_or_refresh(self):
        while self.run:
            try:
                now = datetime.now()
                # Wenn der Access Token fehlt oder bald abläuft, handle die Erneuerung
                if self.access_token is None or self.renewal_threshold < now:
                    if self.refresh_token:
                        try:
                            self.__refresh_token()
                        except Exception:
                            # Wenn Refresh fehlschlägt, erzwinge kompletten neuen Login
                            self.__get_token()
                    else:
                        self.__get_token()
                
                # Aktualisierung der globalen Variablen für die Anzeige
                if self.expires_at:
                    remaining_access = self.expires_at - now
                    g.token_access_expires_in = self.__format_timedelta(remaining_access) if remaining_access.total_seconds() > 0 else "Expired"

                # Setze den Status basierend auf der Existenz des Refresh Tokens
                g.token_refresh_status = "Valid" if self.refresh_token else "Missing"

            except Exception as e:
                self.access_token = None
                self.refresh_token = None
                g.token_refresh_status = "Login Failed"
                print(f"Token processing failed: {e}")

            gevent.sleep(self.tick)
                
    def start(self):
        self.t = gevent.spawn(self.__get_or_refresh)
        return self.t
    
    def stop(self):
        self.run = False
        if self.t and not self.t.dead:
            self.t.kill()
        print("Keycloak-Client EXIT")