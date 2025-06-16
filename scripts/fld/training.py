from learning.modules.fld import FLD
from learning.modules.plotter import Plotter
from learning.modules.gmm import GaussianMixture
from learning.storage.replay_buffer import ReplayBuffer
from learning.storage.distribution_buffer import DistributionBuffer
import torch
import torch.nn as nn
import torch.optim as optim
import matplotlib.pyplot as plt

from torch.utils.tensorboard import SummaryWriter
import wandb

class FLDTraining:
    def __init__(self,
                 log_dir,
                 latent_dim,
                 observation_horizon,
                 num_consecutives,
                 state_idx_dict,
                 state_transitions_data,
                 state_transitions_mean,
                 state_transitions_std,
                 fld_encoder_shape=None,
                 fld_decoder_shape=None,
                 fld_learning_rate=0.0001,
                 fld_weight_decay=0.0005,
                 fld_num_mini_batches=80,
                 device="cuda",
                 loss_function="mse", # mse or geometric
                 noise_level=0.0,
                 loss_horizon_discount=1.0,
                 args=None,
                 ) -> None:
        self.num_motions, self.num_trajs, self.num_groups, self.num_steps, self.observation_dim = state_transitions_data.size()
        self.log_dir = log_dir
        self.latent_dim = latent_dim
        self.observation_horizon = observation_horizon
        self.num_consecutives = num_consecutives
        self.state_transitions_data = state_transitions_data
        self.state_transitions_mean = state_transitions_mean
        self.state_transitions_std = state_transitions_std
        self.fld_num_mini_batches = fld_num_mini_batches
        self.device = device
        self.loss_function = loss_function
        self.noise_level = noise_level
        self.loss_horizon_discount = loss_horizon_discount
        self.args=args
        self.writer = SummaryWriter(log_dir=log_dir, flush_secs=10)
        
        self.loss_state_idx_dict = {}
        current_length = 0
        for state, ids in state_idx_dict.items():
            if (state != "base_pos") and (state != "base_quat"):
                self.loss_state_idx_dict[state] = list(range(current_length, current_length + len(ids)))
                current_length = current_length + len(ids)
                
        self.loss_scale = torch.ones(1, self.observation_horizon, self.observation_dim, device=self.device, dtype=torch.float, requires_grad=False)
        if self.loss_function == "geometric":
            for state, ids in self.loss_state_idx_dict.items():
                if "base_lin_vel" in state:
                    self.loss_scale[..., ids] = 2.0
                elif "base_ang_vel" in state:
                    self.loss_scale[..., ids] = 0.5
                elif "projected_gravity" in state:
                    self.loss_scale[..., ids] = 1.0
                elif "dof_pos" in state:
                    self.loss_scale[..., ids] = 1.0
                elif "dof_vel" in state:
                    self.loss_scale[..., ids] = 0.5
        self.loss_scale *= torch.pow(self.loss_horizon_discount, torch.arange(self.observation_horizon, device=self.device, dtype=torch.float, requires_grad=False)).view(1, -1, 1)

        self.fld = FLD(self.observation_dim, self.observation_horizon, self.latent_dim, self.device, encoder_shape=fld_encoder_shape, decoder_shape=fld_decoder_shape)
        self.fld_optimizer = optim.Adam(self.fld.parameters(), lr=fld_learning_rate, weight_decay=fld_weight_decay)
        
        self.replay_buffer_size = self.num_motions * self.num_trajs * self.num_groups
        self.state_transitions = ReplayBuffer(self.observation_dim, self.num_steps, self.replay_buffer_size, self.device)
        self.state_transitions.insert(self.state_transitions_data.flatten(0, 2))
        
        self.distribution_frequency = DistributionBuffer(self.latent_dim, 20000, self.device)
        self.distribution_amplitude = DistributionBuffer(self.latent_dim, 20000, self.device)
        self.distribution_offset = DistributionBuffer(self.latent_dim, 20000, self.device)

        self.plotter = Plotter()
        self.fig0, self.ax0 = plt.subplots(1, 3)
        self.fig1, self.ax1 = plt.subplots(6, 1)
        self.fig2, self.ax2 = plt.subplots(8, 5)
        self.fig3, self.ax3 = plt.subplots()
        
        self.current_learning_iteration = 0


    def compute_loss(self, input, target):
        input_original = input * self.state_transitions_std + self.state_transitions_mean
        target_original = target * self.state_transitions_std + self.state_transitions_mean
        return torch.mean(torch.sum(torch.square((input_original - target_original) * self.loss_scale), dim=-1))
    
    def compute_z_loss(self, input, target):
        return torch.mean(torch.sum(torch.square(input - target), dim=[0,2]))

        
    def train(self, max_iterations=1000):
        print("[FLD] Training started.")
        tot_iter = self.current_learning_iteration + max_iterations
        mean_fld_loss, mean_z_loss = 0, 0
        for it in range(self.current_learning_iteration, tot_iter):
            state_transitions_data_generator = self.state_transitions.feed_forward_generator(
                self.fld_num_mini_batches,
                self.num_motions * self.num_trajs * self.num_groups // self.fld_num_mini_batches
            )
            for batch_state_transitions in state_transitions_data_generator:
                batch = batch_state_transitions.unfold(1, self.observation_horizon, 1)
                batch_noised = batch + torch.randn_like(batch, device=self.device) * self.noise_level
                batch_input = batch_noised[:, 0, :, :]
                pred_dynamics, latent, signal, params, z_target = self.fld.forward(batch_input, k=self.num_consecutives)
                z_pred=self.fld.z_forward(pred_dynamics)
                phase, frequency, amplitude, offset = params
                
                # reconstruction loss
                loss, z_loss = 0, 0
                for i in range(self.num_consecutives):
                    reconstruction_loss = self.compute_loss(pred_dynamics[i, :, :, :].swapaxes(-2, -1), batch.swapaxes(-2, -1)[:, i])
                    loss += reconstruction_loss
                z_loss=self.compute_z_loss(z_pred, z_target)
                mean_fld_loss += loss.item()
                mean_z_loss += z_loss.item()
                self.fld_optimizer.zero_grad()
                (loss+self.args.beta_scae*z_loss).backward() # if use scae, please use this line
                # loss.backward() # if use fld, please use this line
                self.fld_optimizer.step()

                self.distribution_frequency.insert(frequency.detach())
                self.distribution_amplitude.insert(amplitude.detach())
                self.distribution_offset.insert(offset.detach())

            fld_num_updates = self.fld_num_mini_batches
            mean_fld_loss /= fld_num_updates
            mean_z_loss /= fld_num_updates

            self.writer.add_scalar(f"fld/loss", mean_fld_loss, it)
            self.writer.add_scalar(f"fld/z_loss", mean_z_loss, it)
            if self.args.use_wandb:
                wandb.log({"fld/loss":mean_fld_loss, "fld/z_loss": mean_z_loss}, step=it)
            
            print(f"[FLD] Training iteration {it}/{self.current_learning_iteration + max_iterations}.")

            if it % self.args.figure_log_interval == 0:
                self.save(it)
                with torch.no_grad():
                    self.fld.eval()
                    plot_traj_index = 0
                    self.plotter.plot_distribution(self.ax0[0], self.distribution_frequency.get_distribution(), title="Frequency Distribution")
                    self.plotter.plot_distribution(self.ax0[1], self.distribution_amplitude.get_distribution(), title="Amplitude Distribution")
                    self.plotter.plot_distribution(self.ax0[2], self.distribution_offset.get_distribution(), title="Offset Distribution")
                    self.writer.add_figure("fld/param_distribution", self.fig0, it)
                    if self.args.use_wandb:
                        wandb.log({"fld/param_distribution": wandb.Image(self.fig0)}, step=it)
                    eval_manifold_collection = []

                    for i in range(self.num_motions):
                        eval_traj = self.state_transitions_data[i, 0, :, :self.observation_horizon, :].swapaxes(1, 2)
                        pred_dynamics, latent, signal, params, _ = self.fld(eval_traj)
                        pred = pred_dynamics[0]
                        self.plotter.plot_curves(self.ax1[0], eval_traj[plot_traj_index], -1.0, 1.0, -5.0, 5.0, title="Motion Curves" + " " + str(self.fld.input_channel) + "x" + str(self.observation_horizon), show_axes=False)
                        self.plotter.plot_curves(self.ax1[1], latent[plot_traj_index], -1.0, 1.0, -2.0, 2.0, title="Latent Convolutional Embedding" + " " + str(self.latent_dim) + "x" + str(self.observation_horizon), show_axes=False)
                        self.plotter.plot_circles(self.ax1[2], params[0][plot_traj_index], params[2][plot_traj_index], title="Learned Phase Timing"  + " " + str(self.latent_dim) + "x" + str(2), show_axes=False)
                        self.plotter.plot_curves(self.ax1[3], signal[plot_traj_index], -1.0, 1.0, -2.0, 2.0, title="Latent Parametrized Signal" + " " + str(self.latent_dim) + "x" + str(self.observation_horizon), show_axes=False)
                        self.plotter.plot_curves(self.ax1[4], pred[plot_traj_index], -1.0, 1.0, -5.0, 5.0, title="Curve Reconstruction" + " " + str(self.fld.input_channel) + "x" + str(self.observation_horizon), show_axes=False)
                        self.plotter.plot_curves(self.ax1[5], torch.vstack((eval_traj[plot_traj_index].flatten(0, 1), pred[plot_traj_index].flatten(0, 1))), -1.0, 1.0, -5.0, 5.0, title="Curve Reconstruction (Flattened)" + " " + str(1) + "x" + str(self.fld.input_channel*self.observation_horizon), show_axes=False)
                        
                        self.writer.add_figure(f"fld/reconstruction/motion_{i}", self.fig1, it)
                        if self.args.use_wandb:
                            wandb.log({f"fld/reconstruction/motion_{i}": wandb.Image(self.fig1)}, step=it)
                        
                        for j in range(self.latent_dim):
                            phase = params[0][:, j]
                            frequency = params[1][:, j]
                            amplitude = params[2][:, j]
                            offset = params[3][:, j]
                            self.plotter.plot_phase_1d(self.ax2[j, 0], phase, amplitude, title=("1D Phase Values" if j==0 else None), show_axes=False)
                            self.plotter.plot_phase_2d(self.ax2[j, 1], phase, amplitude, title=("2D Phase Vectors" if j==0 else None), show_axes=False)
                            self.plotter.plot_curves(self.ax2[j, 2], frequency.unsqueeze(0), -1.0, 1.0, 0.0, 4.0, title=("Frequencies" if j==0 else None), show_axes=False)
                            self.plotter.plot_curves(self.ax2[j, 3], amplitude.unsqueeze(0), -1.0, 1.0, 0.0, 1.0, title=("Amplitudes" if j==0 else None), show_axes=False)
                            self.plotter.plot_curves(self.ax2[j, 4], offset.unsqueeze(0), -1.0, 1.0, -1.0, 1.0, title=("Offsets" if j==0 else None), show_axes=False)

                        self.writer.add_figure(f"fld/channel_params/motion_{i}", self.fig2, it)
                        if self.args.use_wandb:
                            wandb.log({f"fld/channel_params/motion_{i}": wandb.Image(self.fig2)}, step=it)
                        
                        phase = params[0]
                        amplitude = params[2]
                        manifold = torch.hstack(
                            (
                                amplitude * torch.sin(2.0 * torch.pi * phase),
                                amplitude * torch.cos(2.0 * torch.pi * phase),
                                )
                            )
                        eval_manifold_collection.append(manifold.cpu())
                    
                    self.plotter.plot_pca(self.ax3, eval_manifold_collection, "Phase Manifold (" + str(self.num_motions) + " Random Sequences)")
                    self.writer.add_figure("fld/phase_manifold", self.fig3, it)
                    if self.args.use_wandb:
                            wandb.log({"fld/phase_manifold": wandb.Image(self.fig3)}, step=it)

                    self.fld.train()

        self.current_learning_iteration += max_iterations
        self.save(self.current_learning_iteration)
        print("[FLD] Training finished.")

    
    def save(self, it):
        latent_parameterization = torch.cat(
            (
                self.distribution_frequency.get_distribution(),
                self.distribution_amplitude.get_distribution(),
                self.distribution_offset.get_distribution(),
            ), dim=1
        )
        torch.save(
            {
                "state_transitions_mean": self.state_transitions_mean,
                "state_transitions_std": self.state_transitions_std,
                "latent_param_max": latent_parameterization.max(dim=0)[0],
                "latent_param_min": latent_parameterization.min(dim=0)[0],
                "latent_param_mean": latent_parameterization.mean(dim=0),
                "latent_param_std": latent_parameterization.std(dim=0),
                },
            self.log_dir + f"/statistics.pt"
            )
        torch.save(
            {
                "fld_state_dict": self.fld.state_dict(),
                "fld_optimizer_state_dict": self.fld_optimizer.state_dict(),
                "iter": it,
                }, 
            self.log_dir + f"/model_{it}.pt"
            )

    
    def load(self, path, load_optimizer=True):
        print(f"[FLD] Loading model from: {path}.")
        loaded_dict = torch.load(path)
        self.fld.load_state_dict(loaded_dict["fld_state_dict"])
        if load_optimizer:
            self.fld_optimizer.load_state_dict(loaded_dict["fld_optimizer_state_dict"])
        self.current_learning_iteration = loaded_dict["iter"]

    
    def fit_gmm(self, covariance_type="diag"):
        self.fig4, self.ax4 = plt.subplots(1, 3, subplot_kw=dict(projection='polar'))
        self.gmm = GaussianMixture(self.num_motions, self.latent_dim * 3, device=self.device, covariance_type=covariance_type)
        all_state_transitions = self.state_transitions_data[:, :, :, :self.observation_horizon, :].flatten(0, 2).swapaxes(1, 2)
        with torch.no_grad():
            self.fld.eval()
            _, _, _, all_params, _ = self.fld(all_state_transitions)
        all_frequency = all_params[1]
        all_amplitude = all_params[2]
        all_offset = all_params[3]
        print("[FLD] GMM fitting started.")
        self.gmm.fit(torch.cat((all_frequency, all_amplitude, all_offset), dim=1))
        print("[FLD] GMM fitting finished.")
        mu, var = self.gmm.get_block_parameters(self.latent_dim)
        self.plotter.plot_gmm(self.ax4[0], all_frequency.view(self.num_motions, -1, self.latent_dim), mu[0], var[0], title="Frequency GMM")
        self.plotter.plot_gmm(self.ax4[1], all_amplitude.view(self.num_motions, -1, self.latent_dim), mu[1], var[1], title="Amplitude GMM")
        self.plotter.plot_gmm(self.ax4[2], all_offset.view(self.num_motions, -1, self.latent_dim), mu[2], var[2], title="Offset GMM")
        torch.save(
            {
                "gmm_state_dict": self.gmm.state_dict(),
                },
            self.log_dir + f"/gmm.pt"
            )
        plt.show()
