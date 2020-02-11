import numpy as np
from scipy.linalg import cho_solve
import warnings


class Prior():
    """Base class for all priors for the bayesian optimizer.

    The __init__ method and the prior method are implemented here.
    Each child class should implement its own potential method, that will be
    called by the prior method implemented here.

    When used, the prior should be initialized outside the optimizer and the
    Prior object should be passed as a function to the optimizer.
    """
    def __init__(self):
        """Basic prior implementation."""

        # By default, do not let the prior use the update method
        self.use_update = False

    def prior(self, x):
        """Actual prior function, common to all Priors"""
        if len(x.shape) > 1:
            n = x.shape[0]
            return np.hstack([self.potential(x[i, :]) for i in range(n)])
        else:
            return self.potential(x)

    def let_update(self):
        if hasattr(self, 'update'):
            self.use_update = True
        else:
            warning = ('The prior does not have implemented an update method ',
                       'the prior has thus not been updated')
            warnings.warn(warning)


class ZeroPrior(Prior):
    """ZeroPrior object, consisting on a constant prior with 0eV energy."""
    def __init__(self):
        Prior.__init__(self)

    def potential(self, x):
        return np.zeros(x.shape[0] + 1)


class ConstantPrior(Prior):
    """Constant prior, with energy = constant and zero forces

    Parameters:

    constant: energy value for the constant.

    Example:

    >>> from ase.optimize import GPMin
    >>> from ase.optimize.gpmin.prior import ConstantPrior
    >>> op = GPMin(atoms, Prior = ConstantPrior(10)
    """
    def __init__(self, constant):
        self.constant = constant
        Prior.__init__(self)

    def potential(self, x):
        d = x.shape[0]
        output = np.zeros(d + 1)
        output[0] = self.constant
        return output

    def set_constant(self, constant):
        self.constant = constant

    def update(self, x, y, L):
        """
        Update the constant to maximize the marginal likelihood.
        The optimization problem:
        m = argmax [-1/2 (y-m).T K^-1(y-m)]
        can be turned into an algebraic problem
        m = [ u.T K^-1 y]/[u.T K^-1 u]

        where u is the constant prior with energy 1 (eV).

        parameters:
        ------------
        x: training features
        y: training targets
        L: Cholesky factor of the kernel
        """

        # Get derivative of prior respect to constant: we call it u
        self.set_constant(1.)
        u = self.prior(x)

        # w = K\u
        w = cho_solve((L, True), u, check_finite=False)

        # Set constant
        m = np.dot(w, y.flatten()) / np.dot(w, u)
        self.set_constant(m)


class CalculatorPrior(Prior):
    """CalculatorPrior object, allows the user to
    use another calculator as prior function instead of the
    default constant.

    Parameters:

    atoms: the Atoms object
    calculator: one of ASE's calculators
    """
    def __init__(self, atoms, calculator):
        Prior.__init__(self)
        self.atoms = atoms.copy()
        self.atoms.set_calculator(calculator)

    def potential(self, x):
        self.atoms.set_positions(x.reshape(-1, 3))
        V = self.atoms.get_potential_energy(force_consistent=True)
        gradV = -self.atoms.get_forces().reshape(-1)
        return np.append(np.array(V).reshape(-1), gradV)
