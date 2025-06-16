##
# Locomotion environments.
##
# fmt: off
from .base.legged_robot import LeggedRobot
from .mit_humanoid.mit_humanoid import MITHumanoid
from .mit_humanoid.mit_humanoid_config import (
    MITHumanoidFlatCfg, 
    MITHumanoidFlatCfgPPO
)

from .mit_humanoid.boi_humanoid import BOIHumanoid
from .mit_humanoid.boi_humanoid_config import (
    BOIHumanoidFlatCfg, 
    BOIHumanoidFlatCfgPPO
)

# fmt: on

##
# Task registration
##
from humanoid_gym.utils.task_registry import task_registry

task_registry.register("mit_humanoid", MITHumanoid, MITHumanoidFlatCfg, MITHumanoidFlatCfgPPO)
task_registry.register("boi_humanoid", BOIHumanoid, BOIHumanoidFlatCfg, BOIHumanoidFlatCfgPPO)