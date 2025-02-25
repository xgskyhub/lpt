import jax
import lpt
from mpi4py import MPI
import argparse
import sys
from time import time
import numpy as np
import jax.numpy as jnp

jax.config.update("jax_enable_x64", True)
# print(jax.config.jax_default_device, jax.local_devices(), jax.local_device_count(), jax.devices())

def _test_transfer():
    k  = np.logspace(-3,2,1000)
    pk = np.sqrt(1e5 * (k/1e-2) * ((1+(k/1e-2)**2)/2)**-4) # something reasonable for testing purposes
    return np.array([k,pk])

def myprint(*args,**kwargs):
    print("".join(map(str,args)),**kwargs);  sys.stdout.flush()

def _profiletime(task_tag, step, times, comm=None, mpiproc=0):
    if comm is not None:
        comm.Barrier()

    dt = time() - times['t0']
    if step in times.keys():
        times[step] += dt
    else:
        times[step] = dt
    times['t0'] = time()

    if mpiproc!=0:
        return times

    if task_tag is not None:
        myprint(f'{task_tag}: {dt:.6f} sec for {step}')
    else:
        myprint(f'{dt:.6f} sec for {step}')
    myprint("")

    return times

times={'t0' : time()}

parser = argparse.ArgumentParser(description='Commandline interface to lpt4py example')
parser.add_argument('--N',     type=int, help='grid dimention [default = 512]', default=512)
parser.add_argument('--seed',  type=int, help='random seed [default = 13579]',  default=13579)
parser.add_argument('--ityp',  type=str, help='lpt input type [default = delta]',  default='delta')

args = parser.parse_args()

N    = args.N
seed = args.seed
ityp = args.ityp

parallel = False
nproc    = MPI.COMM_WORLD.Get_size()
mpiproc  = MPI.COMM_WORLD.Get_rank()
comm     = MPI.COMM_WORLD
task_tag = "MPI process "+str(mpiproc)

if MPI.COMM_WORLD.Get_size() > 1: parallel = True

if not parallel:
    cube = lpt.Cube(N=N,partype=None)  
else:
    jax.distributed.initialize()
    print("After JAX distributed initialize", jax.config.jax_default_device, jax.local_devices(), jax.local_device_count(), jax.devices())
    cube = lpt.Cube(N=N)
times = _profiletime(None, 'initialization', times, comm, mpiproc)

#### NOISE GENERATION
delta = cube.generate_noise(seed=seed)
times = _profiletime(None, 'noise generation', times, comm, mpiproc)

#### NOISE CONVOLUTION TO OBTAIN DELTA
trans = _test_transfer()
# print(trans.shape)
delta = cube.noise2delta(delta, _test_transfer())
times = _profiletime(None, 'noise convolution', times, comm, mpiproc)

# 2LPT DISPLACEMENTS USING INPUT DELTA ENCODED IN STRING ityp
cube.slpt(infield=ityp,delta=delta)
times = _profiletime(None, '2LPT', times, comm, mpiproc)

# LPT displacements are now in
#   cube.s1x
#   cube.s1y
#   cube.s1z
# and
#   cube.s2x
#   cube.s2y
#   cube.s2z
