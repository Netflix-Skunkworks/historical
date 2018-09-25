"""
.. module: historical.mapping
    :platform: Unix
    :copyright: (c) 2017 by Netflix Inc., see AUTHORS for more
    :license: Apache, see LICENSE for more details.
.. author:: Mike Grima <mgrima@netflix.com>
"""

import os

from historical.security_group.models import CurrentSecurityGroupModel, DurableSecurityGroupModel
from historical.s3.models import CurrentS3Model, DurableS3Model
from historical.vpc.models import CurrentVPCModel, DurableVPCModel

# The HISTORICAL_TECHNOLOGY variable MUST be equal to that of an existing model's 'tech' Meta field.
HISTORICAL_TECHNOLOGY = os.environ.get('HISTORICAL_TECHNOLOGY')

# Current Table Mapping:
CURRENT_MAPPING = {
    CurrentSecurityGroupModel.Meta.tech: CurrentSecurityGroupModel,
    CurrentS3Model.Meta.tech: CurrentS3Model,
    CurrentVPCModel.Meta.tech: CurrentVPCModel
}

# Durable Table Mapping:
DURABLE_MAPPING = {
    DurableSecurityGroupModel.Meta.tech: DurableSecurityGroupModel,
    DurableS3Model.Meta.tech: DurableS3Model,
    DurableVPCModel.Meta.tech: DurableVPCModel
}
