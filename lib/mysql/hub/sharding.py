"""This module contains the plumbing necessary for creating, modifying and
querying the sharding information from the state stores.
"""
import uuid as _uuid

import mysql.hub.errors as _errors
import mysql.hub.persistence as _persistence

from mysql.hub.server import MySQLServer, Group

class ShardMapping(_persistence.Persistable):
    """Represents the mapping between the sharding scheme and the table being
    sharded. The class encapsulates the operations required to manage the
    information in the state store related to this mapping.

    The information in the state store in the case where the state store is a
    relational store takes the following form:

    +------------+-------------+-----------+---------------+
    | table_name | column_name | type_name | specification |
    +------------+-------------+-----------+---------------+
    | db1.t1     | userID      | RANGE     | first         |
    +------------+-------------+-----------+---------------+
    | db1.t2     | userID      | RANGE     | second        |
    +------------+-------------+-----------+---------------+
    | db2.t3     | CustomerID  | HASH      | third         |
    +------------+-------------+-----------+---------------+

    The columns are explained as follows

    * table_name - the table being sharded.
    * column_name - the column being sharded.
    * type_name - the type of sharding scheme being used
    * specification - the name of the sharding scheme used to shard this table.

    """

    #Create the schema for the table used to store the shard specification
    #mapping information
    CREATE_SHARD_MAPPING = ("CREATE TABLE shard_mapping"
                            "(table_name VARCHAR(64) "
                            "NOT NULL PRIMARY KEY, "
                            "column_name VARCHAR(64) NOT NULL, "
                            "type_name   VARCHAR(64) NOT NULL, "
                            "INDEX(type_name), "
                            "sharding_specification VARCHAR(64) "
                            "NOT NULL)")

    #Drop the scheme for the table used to store the shard specification
    #mapping information
    DROP_SHARD_MAPPING = ("DROP TABLE shard_mapping")

    #Insert the shard specification mapping information for a table.
    INSERT_SHARD_MAPPING = ("INSERT INTO shard_mapping VALUES"
                            "(%s, %s, %s, %s)")

    #select the shard specification mapping information for a table
    SELECT_SHARD_MAPPING = ("SELECT table_name, column_name, type_name, "
                            "sharding_specification "
                            "FROM shard_mapping "
                            "WHERE table_name = %s")

    #Select all the shard specifications of a particular sharding type.
    SELECT_SHARD_MAPPINGS = ("SELECT table_name, column_name, type_name, "
                            "sharding_specification FROM shard_mapping "
                            "WHERE type_name = %s")

    #Delete the sharding specification to table mapping for a given table.
    DELETE_SHARD_MAPPING = ("DELETE FROM shard_mapping WHERE table_name = %s")


    def __init__(self, table_name, column_name, type_name,
                 sharding_specification):
        """Initialize the Shard Specification Mapping for a given table.

        :param table_name: The table for which the mapping is being created.
        :param column_name: The column name on which the mapping is being
                            defined. The column is useful when resharding
                            comes into the picture.
        :param type_name: The type of sharding defined on the given table.
                            E.g. RANGE, HASH etc.
        :param sharding_specification: The name of the sharding specification
                                        that is used to shard this table.
        """
        super(ShardMapping, self).__init__()
        self.__table_name = table_name
        self.__column_name = column_name
        self.__type_name = type_name
        self.__sharding_specification = sharding_specification

    @property
    def table_name(self):
        """Return the table on which the shard mapping is defined.
        """
        return self.__table_name

    @property
    def column_name(self):
        """Return the column in the table on which the sharding is defined.
        """
        return self.__column_name

    @property
    def type_name(self):
        """Return the type of the sharding specification defined on the table.
        """
        return self.__type_name

    @property
    def sharding_specification(self):
        """The name of the shard specification used to shard the given table.
        """
        return self.__sharding_specification

    @staticmethod
    def list(sharding_type, persister=None):
        """The method returns all the shard mappings (names) of a
        particular sharding_type. For example if the method is called
        with 'range' it returns all the sharding specifications that exist
        of type range.

        :param sharding_type: The sharding type for which the sharding
                              specification needs to be returned.
        :param persister: A valid handle to the state store.

        :return: A list of sharding specification names that are of the
                  sharding type.
        :raises: Sharding Error if Sharding type is not found.
        """

        shard_mappings = []
        cur = persister.exec_stmt(ShardMapping.SELECT_SHARD_MAPPINGS,
                                  {"raw" : False,
                                  "fetch" : False,
                                  "params" : (sharding_type,)})
        rows = cur.fetchall()
        for row in rows:
            shard_mappings.append(ShardMapping(row[0], row[1], row[2],
                                               row[3]))
        if shard_mappings == []:
            raise _errors.ShardingError("Unknown Sharding Type")
        return shard_mappings


    def remove(self, persister=None):
        """Remove the shard mapping represented by the Shard Mapping object.
        The method basically results in removing the association between a
        table and the sharding specification used to shard this table.

        :param persister: Represents a valid handle to the state
                          store.
        :return: True if the remove succeeded.
                False if the query failed.
        """

        persister.exec_stmt(
            ShardMapping.DELETE_SHARD_MAPPING,
            {"params":(self.__table_name,)})
        return True

    @staticmethod
    def create(persister=None):
        """Create the schema to store the mapping between the table and
        the sharding specification.

        :param persister: A valid handle to the state store.
        :return: True if the query succeeded but there is no result set
                False if the query failed
        """

        persister.exec_stmt(ShardMapping.CREATE_SHARD_MAPPING)
        return True

    @staticmethod
    def drop(persister=None):
        """Drop the schema for the table used to store the mapping between
        the table and the sharding specificaton.

        :param persister: A valid handle to the state store.
        :return: True if the query succeeded but there is no result set
                False if the query failed
        """

        persister.exec_stmt(ShardMapping.DROP_SHARD_MAPPING)
        return True

    @staticmethod
    def fetch(table_name, persister=None):
        """Fetch the shard specification mapping for the given table

        :param table_name: The name of the table for which the sharding
                            specification is being queried.
        :param persister: A valid handle to the state store.
        :return: The ShardMapping object that encapsulates the shard mapping
                    information for the given table.
        :raises: Sharding Error if the table name is not found.
        """
        cur = persister.exec_stmt(
                                  ShardMapping.SELECT_SHARD_MAPPING,
                                  {"raw" : False,
                                  "fetch" : False,
                                  "params" : (table_name,)})
        row = cur.fetchone()
        if row is None:
            raise _errors.ShardingError("Table Name Not found")
        if row:
            return ShardMapping(row[0], row[1], row[2], row[3])

    @staticmethod
    def add(table_name, column_name, type_name, sharding_specification,
            persister=None):
        """Add the shard specification mapping information for the
        given table.

        :param table_name: The name of the table being sharded.
        :param column_name: The column whose value is used in the sharding
                            scheme being applied
        :param type_name: The type of sharding being used, RANGE, HASH etc.
        :param sharding_specification: The name of the sharding specification
                                        the given table is being mapped to.
        :param persister: A valid handle to the state store.

        :return: The ShardMapping object for the mapping created.
                 None if the insert failed.

        """
        persister.exec_stmt(
            ShardMapping.INSERT_SHARD_MAPPING,
            {"params":(table_name, column_name,
            type_name, sharding_specification)})
        return ShardMapping(table_name, column_name,
                            type_name,
                            sharding_specification)

class RangeShardingSpecification(_persistence.Persistable):
    """Represents a RANGE sharding specification. The class helps encapsulate
    the representation of a typical RANGE sharding implementation in the
    state store.

    A typical RANGE sharding representation looks like the following,

    +----------------------+------+------+-----------------------+
    |         NAME         | LB   | UB   | GROUP_ID              |
    +----------------------+------+------+-----------------------+
    | FIRST                |    0 | 1000 | GroupID1              |
    +----------------------+------+------+-----------------------+
    | FIRST                | 1001 | 2000 | GroupID2              |
    +----------------------+------+------+-----------------------+
    | FIRST                | 2001 | 3000 | GroupID3              |
    +----------------------+------+------+-----------------------+

    The columns in the above table are explained as follows,

    * NAME - The name of the sharding specification
    * LB -The lower bound of the given RANGE sharding scheme instance
    * UB - The upper bound of the given RANGE sharding scheme instance
    * GROUP_ID - The Group ID that the sharding scheme maps to. This should
                 possibly be the Group group_id that can then be used to load
                 the corresponding server object.
    """

#TODO: Create Forgein keys and Indexes for the table.
    #Create the schema for storing the RANGE sharding specificaton.
    CREATE_RANGE_SPECIFICATION = ("CREATE TABLE "
                                "range_sharding_specification "
                                "(name VARCHAR(64) NOT NULL, "
                                "INDEX(name), "
                                "lower_bound INT, "
                                "upper_bound INT, "
                                "INDEX(lower_bound, upper_bound), "
                                "group_id VARCHAR(64))")

    #Create the referential integrity constraint with the groups table
    ADD_FOREIGN_KEY_CONSTRAINT_GROUP_ID = \
                                ("ALTER TABLE range_sharding_specification "
                                  "ADD CONSTRAINT fk_group_id_sharding_spec "
                                  "FOREIGN KEY(group_id) REFERENCES "
                                  "groups(group_id)")

    #Drop the referential integrity constraint with the groups table
    DROP_FOREIGN_KEY_CONSTRAINT_GROUP_ID = \
                                    ("ALTER TABLE range_sharding_specification "
                                   "DROP FOREIGN KEY fk_group_id_sharding_spec")

    #Drop the schema for storing the RANGE sharding specification.
    DROP_RANGE_SPECIFICATION = ("DROP TABLE "
                                "range_sharding_specification")

    #Insert a RANGE of keys and the server to which they belong.
    INSERT_RANGE_SPECIFICATION = ("INSERT INTO "
                                  "range_sharding_specification "
                                  "VALUES(%s, %s, %s, %s)")

    #Delete a given RANGE specification instance.
    DELETE_RANGE_SPECIFICATION = ("DELETE FROM "
                                  "range_sharding_specification "
                                  "WHERE "
                                  "name = %s AND "
                                  "lower_bound = %s AND "
                                  "upper_bound = %s")

    #Given a sharding scheme name select all the RANGE mappings that it
    #defines.
    SELECT_RANGE_SPECIFICATION = ("SELECT lower_bound, upper_bound, "
                                  "group_id "
                                  "FROM range_sharding_specification "
                                  "WHERE name = %s")

    #Select the server corresponding to the RANGE to which a given key
    #belongs
    LOOKUP_KEY = ("SELECT lower_bound, upper_bound, group_id "
                  "FROM range_sharding_specification "
                  "WHERE %s >= lower_bound AND %s <= upper_bound AND "
                  "name = %s")

    def __init__(self, name, lower_bound, upper_bound, group_id):
        """Initialize a given RANGE sharding mapping specification.

        :param name: The sharding specification to which the
                                    RANGE definition belongs.
        :param lower_bound: The lower bound of the given RANGE sharding defn
        :param upper_bound: The upper bound of the given RANGE sharding defn
        :param group_id: The Group UUID that identfies a Group that contains
                            the data for any key that falls within the RANGE.
        """
        super(RangeShardingSpecification, self).__init__()
        self.__name = name
        self.__lower_bound = lower_bound
        self.__upper_bound = upper_bound
        self.__group_id = group_id

    @property
    def name(self):
        """Return the sharding scheme name to which this RANGE definition
        belongs.
        """
        return self.__name

    @property
    def lower_bound(self):
        """Return the lower bound of this RANGE specification.
        """
        return self.__lower_bound

    @property
    def upper_bound(self):
        """Return the upper bound of this RANGE specification.
        """
        return self.__upper_bound

    @property
    def group_id(self):
        """Return the Group UUID in which the given RANGE resides. This
        uniquely identifies the Group. This can then be used to retrieve
        the Server object to which we can connect.
        """
        return self.__group_id

    def remove(self, persister=None):
        """Remove the RANGE specification mapping represented by the current
        RANGE shard specification object.

        :param persister: Represents a valid handle to the state store.
        :return: True if the remove succeeded
                False if the query failed
        """
        persister.exec_stmt(
            RangeShardingSpecification.DELETE_RANGE_SPECIFICATION,
            {"params":(self.__name,
                       self.__lower_bound,
                       self.__upper_bound)})
        return True

    @staticmethod
    def add(name, lower_bound, upper_bound, group_id, persister=None):
        """Add the RANGE shard specification. This represents a single instance
        of a shard specification that maps a key RANGE to a server.

        :param name: The name of the sharding scheme to which
                                    this definition belongs.
        :param lower_bound: The lower bound of the range sharding definition.
        :param upper_bound: The upper bound of the range sharding definition
        :param group_id: The unique identifier of the Group where the
                            current KEY range belongs.
        :param persister: A valid handle to the state store.

        :return: A RangeShardSpecification object representing the current
                Range specification.
                None if the insert into the state store failed
        """
        persister.exec_stmt(
                  RangeShardingSpecification.INSERT_RANGE_SPECIFICATION,
                                     {"params":(name,
                                                lower_bound,
                                                upper_bound,
                                                group_id)})
        return RangeShardingSpecification(name, lower_bound,
                                          upper_bound, group_id)

    @staticmethod
    def create(persister=None):
        """Create the schema to store the current RANGE sharding specification.

        :param persister: A valid handle to the state store.

        :return: True if the query succeeded but there is no result set
                False if the query failed
        """

        persister.exec_stmt(
                    RangeShardingSpecification.CREATE_RANGE_SPECIFICATION)
        return True

    @staticmethod
    def drop(persister=None):
        """Drop the Range shard specification schema.

        :param persister: A valid handle to the state store.

        :return: True if the query succeeded but there is no result set
                False if the query failed
        """
        persister.exec_stmt(
                        RangeShardingSpecification.DROP_RANGE_SPECIFICATION)
        return True

    @staticmethod
    def add_constraints(persister=None):
        """Add the constraints on the sharding tables.

        :param persister: The DB server that can be used to access the
                          state store.
        """
        persister.exec_stmt(
                RangeShardingSpecification.ADD_FOREIGN_KEY_CONSTRAINT_GROUP_ID)
        return True

    @staticmethod
    def drop_constraints(persister=None):
        """Drop the constraints on the sharding tables.

        :param persister: The DB server that can be used to access the
                  state store.
        """
        persister.exec_stmt(
            RangeShardingSpecification.DROP_FOREIGN_KEY_CONSTRAINT_GROUP_ID)
        return True

    @staticmethod
    def fetch(name, persister=None):
        """Return the RangeShardingSpecification objects corresponding to the
        given sharding scheme.

        :param name: The sharding specifications whose RANGE
                                    definition are fetched.
        :param persister: A valid handle to the state store.

        :return: A  list of RangeShardingSpecification objects which belong to
                to this shard specification.
                None if the sharding scheme name is not found
        :raises: Sharding Error if the Sharding Specification is not found.
        """
        range_sharding_specifications = []
        cur = persister.exec_stmt(
                    RangeShardingSpecification.SELECT_RANGE_SPECIFICATION,
                        {"raw" : False,
                        "fetch" : False,
                        "params" : (name,)})
        rows = cur.fetchall()
        for row in rows:
            range_sharding_specifications.append(RangeShardingSpecification
                                                  (name,
                                                   row[0], row[1], row[2]))
        if range_sharding_specifications == []:
            raise _errors.ShardingError("Sharding specification not found")
        return  range_sharding_specifications

    @staticmethod
    def lookup(key, name, persister=None):
        """Return the Range sharding specification in whose key range the input
            key falls.

        :param key: The key which needs to be checked to see which range it
                    falls into
        :param name: The name of sharding scheme definitions that need to be
                    looked up for the key
        :param persister: A valid handle to the state store.

        :return: The Range Sharding Specification that contains the range in
                which the key belongs.
        :raises: Sharding Error if the sharding specification is not found
        """
        cur = persister.exec_stmt(
                        RangeShardingSpecification.LOOKUP_KEY,
                        {"raw" : False,
                        "fetch" : False,
                        "params" : (key, key, name)})
        row = cur.fetchone()
        if row is None:
            raise _errors.ShardingError("Sharding specification not found")
        if row:
            return RangeShardingSpecification(name, row[0], row[1], row[2])

    @staticmethod
    def delete_from_shard_db(table_name):
        """Delete the data from the copied data directories based on the
        sharding configuration uploaded in the sharding tables of the state
        store. The basic logic consists of

        * Querying the sharding scheme name corresponding to the sharding
          table.
        * Querying the sharding key range using the sharding scheme name.
        * Deleting the sharding keys that fall outside the range for a given
          server.

        :param table_name: The table being sharded.

        :return: False If the delete fails
                True if the delete succeeds.
        """

        #Get the shard mapping for the table from the state store.
        shard_mapping = ShardMapping.fetch(table_name)

        #Get the sharding specification from the shard mapping information
        ssharding_specification = shard_mapping.sharding_specification

        #Query the range sharding specifications defined for the given sharding
        #scheme name
        range_sharding_specs = RangeShardingSpecification.fetch \
                                                (sharding_specification)

        #Use the information in each of the range sharding specs to prune the
        #tables.
        for range_sharding_spec in range_sharding_specs:
            #Form the delete query using the shard mapping and the shard spec
            #information
            delete_query = \
                ("DELETE FROM %s WHERE %s NOT BETWEEN %s and %s")% \
                                                (table_name,
                                                shard_mapping.column_name,
                                                range_sharding_spec.lower_bound,
                                                range_sharding_spec.upper_bound)
            #Fetch the Group object  using the group uuid in the range
            #sharding specification table
            group = Group.fetch(range_sharding_spec.group_id)

            #Fetch the master of the group
            master = MySQLServer.fetch(group.master)

            #Get a connection
            master.connect()

            #Fire the DELETE query
            master.exec_stmt(delete_query)
        return True

def lookup(table_name, key):
    """Given a table name and a key return the server where the shard of this
    table can be found

    :param table_name: The table whose sharding specification needs to be
                        looked up.
    :param key: The key value that needs to be looked up

    :return: The master UUID of the Group that contains the range in which the
            key belongs None if lookup fails.
    :raises: Sharding Error if the table name does not map to a Group.
    """
    group = None
    shard_mapping = ShardMapping.fetch(table_name)
    if shard_mapping.type_name == "RANGE":
        range_sharding_specification = RangeShardingSpecification.lookup \
                                    (key,
                                     shard_mapping.sharding_specification)
        group = Group.fetch(str(range_sharding_specification.group_id))
    ret = []
    for server in group.servers():
        ret.append([str(server.uuid), server.address,
                   group.master == server.uuid])
    return ret

def go_fish_lookup(table_name):
    """Given table name return all the servers that contain the shards for
    this table.

    :param table_name: The table whose shards need to be found

    :return: The set of master UUIDs of the Groups that contain the shards of
            the table. None if lookup fails.
    :raises: Sharding Error if the table name does not map to a Group.
    """
    server_list = {}
    shard_mapping = ShardMapping.fetch(table_name)
    if shard_mapping.type_name == "RANGE":
        range_sharding_specifications = RangeShardingSpecification.fetch(
                                    shard_mapping.sharding_specification)
    for range_sharding_specification in range_sharding_specifications:
        group = Group.fetch(str(range_sharding_specification.group_id))
        if group is not None:
            ret = []
            for server in group.servers():
                ret.append([str(server.uuid), server.address,
                           group.master == server.uuid])
            server_list[str(group.group_id)] = ret
    return server_list
