#!/bin/bash
python scripts/finetune.py --task boi_humanoid --headless --num_envs 4096 --dataset mix\
                    --load_run ./logs/flat_mit_humanoid/policy_training/20240527100156_mix
