import meshio
import math
import numpy as np
from pyevtk.hl import unstructuredGridToVTK
from pyevtk.vtk import VtkTriangle

"""
Contains functions to create level sets
"""
# Normalize an array of 3-component vectors
def normalize(a):
    ss = np.sum(a**2, axis=1)**0.5
    a = a / ss[:, np.newaxis]
    return a

# Coordinate conversions
def cart2pol(x, y, z):
    r = np.sqrt(x**2 + y**2)
    rho = np.sqrt(x**2 + y**2 + z**2)
    phi = np.arctan2(r, z)
    theta = np.arctan2(y, x)
    return(rho, phi, theta)

def pol2cart(rho, phi, theta):
    x = rho * np.sin(phi) * np.cos(theta)
    y = rho * np.sin(phi) * np.sin(theta)
    z = rho * np.cos(phi)
    return(x, y, z)

# Convert to polar, add r + k, convert back to cartesian
def add_to_rad(inc, vertices):
    sets = {}
    for i in inc:
        polar_vert = np.array(cart2pol(vertices[:,0], vertices[:,1], vertices[:,2] ) ).T
        polar_vert[:,0] += i
        cart_vert = np.array(pol2cart(polar_vert[:,0], polar_vert[:,1], polar_vert[:,2] ) ).T
        sets[str(i)] = cart_vert
    return(sets)

# Convert to polar, multiply r*k, convert back to cartesian
def mult_rad(inc, vertices):
    sets = {}
    for i in inc:
        polar_vert = np.array(cart2pol(vertices[:,0], vertices[:,1], vertices[:,2] ) ).T
        polar_vert[:,0] *= i
        cart_vert = np.array(pol2cart(polar_vert[:,0], polar_vert[:,1], polar_vert[:,2] ) ).T
        sets[str(i)] = cart_vert
    return(sets)

# Returns dot product of displacement vectors with surface outward normal
def dots(u, vert, conn):

    # Check type
    vert = np.asarray(vert, dtype="float64")
    conn = np.asarray(conn, dtype="int64")

    # Face coordinates
    tris = vert[conn]

    # Face normals
    fn = np.cross( tris[:,1,:] - tris[:,0,:]  , tris[:,2,:] - tris[:,0,:] )

    # Normalize face normals
    fn = normalize(fn)

    # Vertex normal = sum of adjacent face normals
    n = np.zeros(vert.shape, dtype = vert.dtype)
    n[ conn[:,0] ] += fn
    n[ conn[:,1] ] += fn
    n[ conn[:,2] ] += fn

    # Normalize vertex normals
    # Mult by -1 to make them point outward
    n = normalize(n) * -1

    # vertex displacement
    disp = np.array([u(x) for x in vert])

    # normalize row-wise
    disp = normalize(disp)

    # dot products
    dp = np.sum(disp*n, axis=1)

    return dp

def level_sets(sets, vert, conn, u, output_folder="./"):

    # Format inputs
    vert = np.asarray(vert, dtype="float64")
    conn = np.asarray(conn, dtype="int64")

    # number of points/cells
    nvert = np.size(vert, 0)
    ncells = np.size(conn, 0)

    # Create level sets
    set_dict = mult_rad(sets, vert)

    for s in sets:
        points = np.array(set_dict[str(s)], dtype="float64")

        # x,y,z
        x = points[:,0]
        y = points[:,1]
        z = points[:,2]

        # cell types
        ctype = np.zeros(ncells)
        ctype[:] = VtkTriangle.tid

        # ravel conenctivity
        conn_ravel = conn.ravel().astype("int64")

        # offset begins with 1
        offset = 3 * (np.arange(ncells, dtype='int64') + 1)

        # Data
        disp = np.array([u(p) for p in points])
        ux, uy, uz = disp[:,0], disp[:,1], disp[:,2]
        ux = np.ascontiguousarray(ux, dtype=np.float32)
        uy = np.ascontiguousarray(uy, dtype=np.float32)
        uz = np.ascontiguousarray(uz, dtype=np.float32)

        # magnitude
        u_mag = np.sqrt(ux**2 + uy**2 + uz**2)

        # dot product
        u_dot = dots(u, points, conn)

        # signed magnitude
        s_mag = u_mag * np.abs(u_dot) / u_dot

        unstructuredGridToVTK(output_folder + "level_set_" + str(s), x, y, z, connectivity=conn_ravel, offsets=offset, cell_types = ctype, 
        pointData={"u_x" : ux, "u_y" : uy, "u_z" : uz, "u_mag" : u_mag, "u_dot" : u_dot, "u_mag_signed":s_mag})