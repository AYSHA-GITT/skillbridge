import flwr as fl
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
        # Target: binary job-readiness (0 or 1)
        np.random.seed(abs(hash(partition_id)) % (2**32))
        self.X = np.random.uniform(0.2, 0.95, size=(num_samples, 10))
        # Label heuristic: student is ready if skill sum is higher
        self.y = (self.X.mean(axis=1) > 0.55).astype(int)

        self.model = SGDClassifier(loss='log_loss', penalty='l2', max_iter=100, warm_start=True, random_state=42)
        self.model.fit(self.X[:10], self.y[:10]) # Initialize weights

    def get_parameters(self, config=None):
        return [self.model.coef_, self.model.intercept_]

    def set_parameters(self, parameters):
        if len(parameters) >= 2:
            self.model.coef_ = np.array(parameters[0], copy=True)
            self.model.intercept_ = np.array(parameters[1], copy=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        # Train locally on institutional partition
        self.model.partial_fit(self.X, self.y, classes=np.array([0, 1]))
        preds = self.model.predict(self.X)
        local_acc = float((preds == self.y).mean())

        return self.get_parameters(), self.num_samples, {
            'partition_id': self.partition_id,
            'local_accuracy': round(local_acc, 4)
        }

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        preds = self.model.predict(self.X)
        loss = float(((preds - self.y) ** 2).mean())
        acc = float((preds == self.y).mean())
        return loss, self.num_samples, {'accuracy': round(acc, 4)}
