import logging

from buildingmotif.ingresses.base import Record  # noqa
from buildingmotif.ingresses.csv import CSVIngress  # noqa
from buildingmotif.ingresses.template import (  # noqa
    TemplateIngress,
    TemplateIngressWithChooser,
)

try:
    from buildingmotif.ingresses.brick import (  # noqa
        BACnetNetwork,
        BACnetToBrickIngress,
    )
except ImportError as e:
    logging.warning(f"Could not import BACnet ingresses: {e}")
