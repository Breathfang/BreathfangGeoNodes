import numpy as np
from sympy import Matrix

A = Matrix([
    [1, 2, 3, 4],
    [5, 3, 7, 9],
    [9, 5, 11, 10],
    [4, 3, 2, 1]
])

print("A=")
print(A)

# determinant
det = A.det()
print("det(A)=")
print(det)

# adjoint
adj = A.adjugate()
print("adj(A)=")
print(adj)

# cofactor
cof = A.cofactor_matrix()
print("cof(A)=")
print(cof)

input("Press enter to exit...")