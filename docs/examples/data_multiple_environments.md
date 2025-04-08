# Data Across Multiple Environments

Lets say you have an app that you wish to deploy in two environments: staging and production, with the dev VM as the default. A good layout for this would be:

+ ``deploy.py``
+ ``inventories/production.py`` - production inventory
+ ``inventories/staging.py`` - staging inventory
+ ``group_data/all.py`` - shared data
+ ``group_data/production.py`` - production data
+ ``group_data/staging.py`` - staging data

The "all" group data contains any shared info and defaults:

```py
# group_data/all.py

env = 'dev'
git_repo = 'https://github.com/Fizzadar/pyinfra'
```

And the production/staging data describe the differences:

```py
# group_data/production.py

env = 'production'
git_branch = 'master'
```

```py
# group_data/staging.py

env = 'staging'
git_branch = 'develop'
```

For more information on inventory files, see :doc:`inventory-data`.

