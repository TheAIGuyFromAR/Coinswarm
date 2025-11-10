# cloudflare_d1_service.py
# Service class for interacting with Cloudflare D1 from a Python Worker

class CloudflareD1Service:
    """
    Service for connecting to and querying Cloudflare D1 from a Python Worker.

    This class wraps the D1 binding provided by Cloudflare Python Workers.
    It provides convenience methods for CRUD operations and database/table info.

    Official docs: https://developers.cloudflare.com/d1/examples/query-d1-from-python-workers/

    Usage:
        # In your WorkerEntrypoint fetch handler:
        service = CloudflareD1Service(bindings["DB"])
        result = await service.select("my_table")
        # result.rows, result.success, result.error
    """
    def __init__(self, d1_binding):
        """
        Initialize with the D1 binding from Cloudflare Python Workers.
        Args:
            d1_binding: The D1 binding object, e.g. bindings["DB"]
        """
        self.d1 = d1_binding

    async def query(self, sql: str, params=None):
        """
        Run a SQL query against D1.
        Args:
            sql (str): SQL statement (use ? for parameters)
            params (list, optional): List of parameters for the SQL statement
        Returns:
            Result object with .rows, .success, .error (see Cloudflare docs)
        """
        if params is None:
            params = []
        return await self.d1.execute(sql, params)

    async def select(self, table: str, where: str = None, params=None):
        """
        Select records from a table with optional WHERE clause.
        Args:
            table (str): Table name
            where (str, optional): WHERE clause (without 'WHERE')
            params (list, optional): Parameters for WHERE clause
        Returns:
            Result object (.rows, .success, .error)
        """
        sql = f"SELECT * FROM {table}"
        if where:
            sql += f" WHERE {where}"
        return await self.query(sql, params)

    async def insert(self, table: str, data: dict):
        """
        Insert a record into a table.
        Args:
            table (str): Table name
            data (dict): Dictionary of column-value pairs
        Returns:
            Result object
        """
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        sql = f"INSERT INTO {table} ({keys}) VALUES ({placeholders})"
        return await self.query(sql, list(data.values()))

    async def update(self, table: str, data: dict, where: str, params=None):
        """
        Update records in a table with a WHERE clause.
        Args:
            table (str): Table name
            data (dict): Columns and new values
            where (str): WHERE clause (without 'WHERE')
            params (list, optional): Parameters for WHERE clause
        Returns:
            Result object
        """
        set_clause = ', '.join([f"{k}=?" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        all_params = list(data.values())
        if params:
            all_params.extend(params)
        return await self.query(sql, all_params)

    async def delete(self, table: str, where: str, params=None):
        """
        Delete records from a table with a WHERE clause.
        Args:
            table (str): Table name
            where (str): WHERE clause (without 'WHERE')
            params (list, optional): Parameters for WHERE clause
        Returns:
            Result object
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        return await self.query(sql, params)

    async def list_tables(self):
        """
        List all tables in the database.
        Returns:
            Result object with .rows containing table names
        """
        sql = "SELECT name FROM sqlite_master WHERE type='table'"
        return await self.query(sql)

    async def table_info(self, table: str):
        """
        Get information about a table's columns.
        Args:
            table (str): Table name
        Returns:
            Result object with .rows describing columns
        """
        sql = f"PRAGMA table_info({table})"
        return await self.query(sql)

    async def database_info(self):
        """
        Get general information about the database (list tables, etc.).
        Returns:
            Result object (see list_tables)
        """
        return await self.list_tables()
