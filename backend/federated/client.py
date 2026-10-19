from typing import Dict, List, Tuple, Any, cast
import flwr as fl
from flwr.common import NDArrays, Scalar
import numpy as np
import warnings
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import SGDClassifier
warnings.filterwarnings("ignore", category=ConvergenceWarning)


class InstitutionClient(fl.client.NumPyClient):
    """
    Flower NumPyClient simulating a college or university node (e.g., IIT Delhi, NIT Trichy).
    Trains locally on student partition features without transmitting raw resumes or skill matrices.
    """

    def __init__(self, partition_id: str, num_samples: int = 120):
        self.partition_id = partition_id
        self.num_samples = num_samples
        # 10 features: [python, sql, ml, stats, web, cloud, ds_algo, comms, quiz_avg, projects]
        # Ensure deterministic seed per partition across processes
        seed = int.from_bytes(partition_id.encode('utf-8'), 'little') % (2**31 - 1)
        rng = np.random.RandomState(seed)
        self.X = rng.uniform(0.2, 0.95, size=(num_samples, 10))
        # Label heuristic: student is ready if skill sum is higher
        self.y = (self.X.mean(axis=1) > 0.55).astype(int)
        if len(np.unique(self.y)) < 2:
            self.y[0] = 0
            self.y[1] = 1

        self.model = SGDClassifier(loss='log_loss', penalty='l2', max_iter=100, warm_start=True, random_state=42)
        self.model.partial_fit(cast(Any, self.X), cast(Any, self.y), classes=np.array([0, 1])) # Initialize weights with both classes

    def get_parameters(self, config: Dict[str, Scalar] = {}) -> NDArrays:
        return [cast(np.ndarray, self.model.coef_), cast(np.ndarray, self.model.intercept_)]

    def set_parameters(self, parameters: NDArrays) -> None:
        if len(parameters) >= 2:
            self.model.coef_ = cast(Any, np.array(parameters[0], copy=True))
            self.model.intercept_ = cast(Any, np.array(parameters[1], copy=True))

    def fit(self, parameters: NDArrays, config: Dict[str, Scalar]) -> Tuple[NDArrays, int, Dict[str, Scalar]]:
        self.set_parameters(parameters)
        # Train locally on institutional partition
        self.model.partial_fit(cast(Any, self.X), cast(Any, self.y), classes=np.array([0, 1]))
        preds = self.model.predict(cast(Any, self.X))
        local_acc = float((preds == self.y).mean())

        metrics: Dict[str, Scalar] = {
            'partition_id': self.partition_id,
            'local_accuracy': round(local_acc, 4)
        }
        return self.get_parameters(config), self.num_samples, metrics

    def evaluate(self, parameters: NDArrays, config: Dict[str, Scalar]) -> Tuple[float, int, Dict[str, Scalar]]:
        self.set_parameters(parameters)
        preds = self.model.predict(cast(Any, self.X))
        loss = float(((preds - self.y) ** 2).mean())
        acc = float((preds == self.y).mean())
        metrics: Dict[str, Scalar] = {'accuracy': round(acc, 4)}
        return loss, self.num_samples, metrics

