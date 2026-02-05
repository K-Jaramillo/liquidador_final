# -*- coding: utf-8 -*-
"""
Configuración de Firebird 2.5 para Linux y Windows
Maneja la biblioteca embebida y las rutas de manera cross-platform
"""
import os
import sys


class FirebirdSetup:
    """Configuración de Firebird multiplataforma."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._setup_environment()
    
    def _setup_environment(self):
        """Configura el entorno para Firebird según el SO."""
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if sys.platform == 'win32':
            self._setup_windows()
        else:
            self._setup_linux()
    
    def _setup_windows(self):
        """Configuración para Windows."""
        # En Windows, usamos fbclient.dll del sistema o bundled
        self.firebird_lib_path = None  # Usa la del sistema
        self.isql_path = self._find_windows_isql()
        self.fb_library_name = None  # fdb usará el default
        
        # Intentar encontrar fbclient.dll bundled
        bundled_dll = os.path.join(self.base_path, 'firebird', 'fbclient.dll')
        if os.path.exists(bundled_dll):
            self.fb_library_name = bundled_dll
    
    def _setup_linux(self):
        """Configuración para Linux con Firebird 2.5 embebido."""
        self.firebird_lib_path = os.path.join(self.base_path, 'firebird25_lib')
        
        # Verificar si existe la biblioteca bundled de Firebird 2.5
        libfbembed = os.path.join(self.firebird_lib_path, 'libfbembed.so.2.5.9')
        libfbclient = os.path.join(self.firebird_lib_path, 'libfbclient.so.2.5.9')
        
        if os.path.exists(libfbembed):
            self.fb_library_name = libfbembed
        elif os.path.exists(libfbclient):
            self.fb_library_name = libfbclient
        else:
            # Buscar en el sistema
            self.fb_library_name = self._find_system_fbclient()
        
        # Configurar LD_LIBRARY_PATH
        if os.path.exists(self.firebird_lib_path):
            current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
            if self.firebird_lib_path not in current_ld_path:
                os.environ['LD_LIBRARY_PATH'] = f"{self.firebird_lib_path}:{current_ld_path}"
            
            # Configurar FIREBIRD para encontrar security2.fdb y firebird.conf
            os.environ['FIREBIRD'] = self.firebird_lib_path
        
        # Configurar isql
        self.isql_path = self._find_linux_isql()
    
    def _find_windows_isql(self):
        """Busca isql.exe en Windows."""
        posibles_rutas = [
            r'C:\Program Files\Firebird\Firebird_5_0\isql.exe',
            r'C:\Program Files\Firebird\Firebird_4_0\isql.exe',
            r'C:\Program Files\Firebird\Firebird_3_0\isql.exe',
            r'C:\Program Files\Firebird\Firebird_2_5\bin\isql.exe',
            r'C:\Program Files (x86)\Firebird\Firebird_2_5\bin\isql.exe',
            r'C:\Firebird\isql.exe',
            r'C:\Firebird\bin\isql.exe',
        ]
        for ruta in posibles_rutas:
            if os.path.exists(ruta):
                return ruta
        return r'C:\Program Files\Firebird\Firebird_5_0\isql.exe'
    
    def _find_linux_isql(self):
        """Busca isql en Linux."""
        # Primero buscar el bundled de Firebird 2.5
        bundled_isql = os.path.join(self.base_path, 'firebird25_bin', 'isql')
        if os.path.exists(bundled_isql):
            return bundled_isql
        
        # Buscar en ubicaciones del sistema
        posibles_rutas = [
            '/usr/bin/isql-fb',
            '/usr/bin/isql',
            '/opt/firebird/bin/isql',
            '/usr/local/firebird/bin/isql',
        ]
        for ruta in posibles_rutas:
            if os.path.exists(ruta):
                return ruta
        
        # Intentar shutil.which
        import shutil
        isql_in_path = shutil.which('isql-fb') or shutil.which('isql')
        if isql_in_path:
            return isql_in_path
        
        return '/usr/bin/isql-fb'
    
    def _find_system_fbclient(self):
        """Busca fbclient en el sistema Linux."""
        posibles = [
            '/usr/lib/x86_64-linux-gnu/libfbclient.so',
            '/usr/lib64/libfbclient.so',
            '/usr/lib/libfbclient.so',
            '/opt/firebird/lib/libfbclient.so',
        ]
        for lib in posibles:
            if os.path.exists(lib):
                return lib
        return None
    
    def get_connection_params(self, db_path=None):
        """
        Obtiene los parámetros de conexión para fdb.
        
        Args:
            db_path: Ruta a la base de datos. Si es None, usa la default.
            
        Returns:
            dict: Parámetros para fdb.connect()
        """
        if db_path is None:
            db_path = self.get_default_db_path()
        
        params = {
            'database': db_path,
            'user': 'SYSDBA',
            'password': 'masterkey',
        }
        
        # Solo agregar fb_library_name si lo tenemos (modo embebido)
        if self.fb_library_name and os.path.exists(self.fb_library_name):
            params['fb_library_name'] = self.fb_library_name
        
        return params
    
    def get_default_db_path(self):
        """Obtiene la ruta por defecto de la base de datos."""
        if sys.platform == 'win32':
            return r'c:\Users\UsoPersonal\Desktop\Repartidores\PDVDATA.FDB'
        else:
            return os.path.join(self.base_path, 'PDVDATA.FDB')
    
    def get_isql_command_prefix(self):
        """
        Obtiene el prefijo del comando isql con las variables de entorno necesarias.
        
        Returns:
            list: Lista de argumentos para subprocess o string para shell
        """
        if sys.platform == 'win32':
            return [self.isql_path]
        else:
            # En Linux, necesitamos LD_LIBRARY_PATH
            if os.path.exists(self.firebird_lib_path):
                return [
                    'env',
                    f'LD_LIBRARY_PATH={self.firebird_lib_path}:{os.environ.get("LD_LIBRARY_PATH", "")}',
                    f'FIREBIRD={self.firebird_lib_path}',
                    self.isql_path
                ]
            return [self.isql_path]
    
    def get_isql_env(self):
        """
        Obtiene las variables de entorno necesarias para ejecutar isql.
        
        Returns:
            dict: Variables de entorno
        """
        env = os.environ.copy()
        
        if sys.platform != 'win32' and os.path.exists(self.firebird_lib_path):
            current_ld_path = env.get('LD_LIBRARY_PATH', '')
            env['LD_LIBRARY_PATH'] = f"{self.firebird_lib_path}:{current_ld_path}"
            env['FIREBIRD'] = self.firebird_lib_path
        
        return env


# Singleton global para fácil acceso
_firebird_setup = None


def get_firebird_setup():
    """Obtiene la instancia singleton de FirebirdSetup."""
    global _firebird_setup
    if _firebird_setup is None:
        _firebird_setup = FirebirdSetup()
    return _firebird_setup


def get_fdb_connection(db_path=None):
    """
    Crea una conexión fdb con la configuración correcta.
    
    Args:
        db_path: Ruta a la base de datos (opcional)
        
    Returns:
        fdb.Connection: Conexión a la base de datos
    """
    import fdb
    setup = get_firebird_setup()
    params = setup.get_connection_params(db_path)
    return fdb.connect(**params)
