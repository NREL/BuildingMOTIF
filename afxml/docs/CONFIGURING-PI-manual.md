# Server

This name should correspond to the name of the machine hosting the PI Server instance as it appears in your network configuration, or its IP address. Entering the wrong server name will prevent PI Server from loading the model on a PI software module, such as a PI Explorer instance.

# Database

This name should correspond to the PI Server database to which you woud like to copy a new model. This database name should correspond to an existing one if you want to update an existing installation, or to a new name to create a new database.

# Importance of setting everything right

We did not create a routine for searching available databases on a given PI Server instance because of user permission issues.

# Units of Measure

These units of measure should not be modified. They match the AFXML Schema definition for units of measure.