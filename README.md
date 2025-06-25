# Bi-Level Motion Imitation for Humanoid Robots

This repository provides the implementation of [Bi-Level Motion Imitation (BMI)](https://arxiv.org/pdf/2410.01968) algorithm. The method is inspired by and built on top of FLD (https://github.com/mit-biomimetics/fld). 


**Paper**: [Bi-Level Motion Imitation for Humanoid Robots](https://arxiv.org/pdf/2410.01968)  
**Project website**: https://sites.google.com/view/bmi-corl2024 


## Installation

1. Create a new python virtual environment with `python 3.8`
2. Install `pytorch 1.10` with `cuda-11.3`
        
        pip3 install torch==1.10.0+cu113 torchvision==0.11.1+cu113 torchaudio==0.10.0+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html

3. Install Isaac Gym

   - Download and install [Isaac Gym Preview 4](https://developer.nvidia.com/isaac-gym)

        ```
        cd isaacgym/python
        pip install -e .
        ```

   - Try running an example

        ```
        cd examples
        python 1080_balls_of_solitude.py
        ```

   - For troubleshooting, check docs in `isaacgym/docs/index.html`


## Configuration
- We need to use the datasets from FLD (https://github.com/mit-biomimetics/fld) and rearrange all the datasets including the challenging motions under `resources/robots/mit_humanoid/datasets/mix`.


## Usage

### Train the dynamics model by SCAE
```
./run_scae.sh
```
- This command trains the SCAE model to learn a sparse and well-structured dynamics model of human motions.

### Pretrain the robot policy

```
./run_policy.sh
```

- This command trains a robot policy informed by the latent representation of the reference motions.

### Finetune the robot policy and the decoder of SCAE

```
./run_finetune.sh
```

- This command finetunes both the decoder of SCAE and the robot policy under the bi-level optimization framework.



## Citation
```
@inproceedings{zhaobilevel,
  title={Bi-Level Motion Imitation for Humanoid Robots},
  author={Zhao, Wenshuai and Zhao, Yi and Pajarinen, Joni and Muehlebach, Michael},
  booktitle={8th Annual Conference on Robot Learning}
}
```

## References

The code is built upon the open-sourced [Fourier latent dyanmics (FLD)](https://github.com/mit-biomimetics/fld), [Periodic Autoencoder (PAE) Implementation](https://github.com/sebastianstarke/AI4Animation/tree/master/AI4Animation/SIGGRAPH_2022/PyTorch/PAE), [Isaac Gym Environments for Legged Robots](https://github.com/leggedrobotics/legged_gym) and the [PPO implementation](https://github.com/leggedrobotics/rsl_rl). We refer to the original repositories for more details.
