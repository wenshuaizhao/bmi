from humanoid_gym import LEGGED_GYM_ROOT_DIR
from scripts.fld.training import FLDTraining
import os
import torch
from datetime import datetime
import argparse
import wandb
import socket
from pathlib import Path

class FLDExperiment:
    
    def __init__(self, state_idx_dict, observation_horizon, num_consecutives, device, args=None):
        self.state_idx_dict = state_idx_dict
        self.observation_horizon = observation_horizon
        self.num_consecutives = num_consecutives
        self.dim_of_interest = torch.cat(
            [
                torch.tensor(ids, device=device, dtype=torch.long, requires_grad=False)
                for state, ids in state_idx_dict.items()
                if ((state != "base_pos") and (state != "base_quat"))
                ]
            )
        self.device = device
        self.args=args

    def prepare_data(self):
        datasets_root = os.path.join(LEGGED_GYM_ROOT_DIR + f"/resources/robots/mit_humanoid/datasets/{self.args.dataset}")
        motion_data = os.listdir(datasets_root)
        motion_name_set = [data.replace('motion_data_', '').replace('.pt', '') for data in motion_data if "combined" not in data and ".pt" in data]
        motion_data_collection = []

        for i, motion_name in enumerate(motion_name_set):
            motion_path = os.path.join(datasets_root, "motion_data_" + motion_name + ".pt")
            motion_data = torch.load(motion_path, map_location=self.device)[:, :, self.dim_of_interest]
            loaded_num_trajs, loaded_num_steps, loaded_obs_dim = motion_data.size()
            print(f"[Motion Loader] Loaded motion {motion_name} with {loaded_num_trajs} trajectories, {loaded_num_steps} steps with {loaded_obs_dim} dimensions.")
            motion_data_collection.append(motion_data.unsqueeze(0))

        motion_data_collection = torch.cat(motion_data_collection, dim=0)
        self.state_transitions_mean = motion_data_collection.flatten(0, 2).mean(dim=0)
        self.state_transitions_std = motion_data_collection.flatten(0, 2).std(dim=0) + 1e-6

        motion_data_collection = motion_data_collection.unfold(2, self.observation_horizon + self.num_consecutives - 1, 1).swapaxes(-2, -1)
        self.state_transitions_data = (motion_data_collection - self.state_transitions_mean) / self.state_transitions_std

    def train(self, log_dir, latent_dim, args=None):
        fld_training = FLDTraining(
            log_dir,
            latent_dim,
            self.observation_horizon,
            self.num_consecutives,
            self.state_idx_dict,
            self.state_transitions_data,
            self.state_transitions_mean,
            self.state_transitions_std,
            fld_encoder_shape=[64, 64],
            fld_decoder_shape=[64, 64],
            fld_learning_rate=0.0001,
            fld_weight_decay=0.0005,
            fld_num_mini_batches=args.fld_num_mini_batches,
            device="cuda",
            loss_function="geometric",
            noise_level=0.1,
            args=args,
            )
        fld_training.train(max_iterations=args.max_iterations)
        fld_training.fit_gmm(covariance_type="full")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--fld_num_mini_batches', type=int, default=10, help="number of minibatch for training")
    parser.add_argument('--max_iterations', type=int, default=5000, help="number of iterations to train the dynamics model")
    parser.add_argument("--use_wandb", action='store_true', default=False)
    parser.add_argument("--dataset", type=str, default='normal', choices=['normal', 'hard', 'mix'])
    parser.add_argument("--wandb_tag", type=str, default='debug', help="wandb tags")
    parser.add_argument("--figure_log_interval", type=int, default=50, help="number of iterations to log the figures")
    parser.add_argument("--beta_scae", type=float, default=1, help="the coefficient of latent reconstruction error")
    
    args = parser.parse_args()
    state_idx_dict = {
        "base_pos": [0, 1, 2],
        "base_quat": [3, 4, 5, 6],
        "base_lin_vel": [7, 8, 9],
        "base_ang_vel": [10, 11, 12],
        "projected_gravity": [13, 14, 15],
        "dof_pos_leg_l": [16, 17, 18, 19, 20],
        "dof_pos_arm_l": [21, 22, 23, 24],
        "dof_pos_leg_r": [25, 26, 27, 28, 29],
        "dof_pos_arm_r": [30, 31, 32, 33],
    }
    observation_horizon = 51
    latent_dim = 8
    num_consecutives = 50
    device = "cuda"
    log_dir_root = LEGGED_GYM_ROOT_DIR + "/logs/flat_mit_humanoid/fld/dynamics_training/"
    date_time=datetime.now().strftime("%Y%m%d%H%M%S")
    log_dir = log_dir_root + f"{date_time}"

    if args.use_wandb:
        run = wandb.init(config=args,
                            project='fld_dynamics',
                            entity='username_aalto',
                            notes=socket.gethostname(),
                            name=str(args.dataset) + "_" + str(date_time),
                            group=str(args.dataset),
                            dir=Path(log_dir),
                            job_type="training",
                            tags=[f'{args.wandb_tag}'],
                            reinit=True)


    fld_experiment = FLDExperiment(state_idx_dict, observation_horizon, num_consecutives, device, args)
    fld_experiment.prepare_data()
    fld_experiment.train(log_dir, latent_dim, args)
    