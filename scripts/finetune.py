"""
Main script for launching a training session.
"""
# humanoid-gym
from humanoid_gym.envs import task_registry
from humanoid_gym.utils import get_args


def finetune(args):
    env, env_cfg = task_registry.make_env(name=args.task, args=args)
    ppo_runner, train_cfg = task_registry.make_alg_runner(env=env, name=args.task, args=args)
    ppo_runner.finetune(
        num_learning_iterations=train_cfg.runner.max_iterations,
        init_at_random_ep_len=True,
    )


if __name__ == "__main__":
    args = get_args()
    args.finetune=True
    finetune(args)
