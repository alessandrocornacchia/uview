import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
# from sklearn.metrics import classification_report
from torch.utils.data import DataLoader, TensorDataset

# ========= Path Initialization =========
# BASE_DIR = "/home/students/zwang/tmp/microsketch/"
# sys.path.append(BASE_DIR)

# # data directory
# METRICS_DIR = f"{BASE_DIR}/experiments/NSDI26/metrics/"
# if not os.path.exists(METRICS_DIR):
#     print(f"Directory {METRICS_DIR} does not exist.")
#     exit(1)

# # trained model directory
# TRAINED_MODEL_DIR = f"{BASE_DIR}/trained_models/"
# os.makedirs(TRAINED_MODEL_DIR, exist_ok=True)


# ========= VAE Model definition =========
class VAEModule(nn.Module):
    def __init__(self, input_dim, latent_dim):
        super(VAEModule, self).__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
        )
        self.mu = nn.Linear(32, latent_dim)
        self.logvar = nn.Linear(32, latent_dim)

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 64),
            nn.ReLU(),
            nn.Linear(64, input_dim),
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.mu(h), self.logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, logvar = self.encode(x)
        z = self.reparameterize(mu, logvar)
        x_recon = self.decode(z)
        return x_recon, mu, logvar


def loss_function(x, x_recon, mu, logvar):
    recon_loss = F.mse_loss(x_recon, x, reduction="sum")
    kl_div = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return recon_loss + kl_div


# ========= VAE Wrapper =========
class VAE:
    def __init__(
        self, input_dim, latent_dim=10, batch_size=32, epochs=50, verbose=False
    ):
        self.batch_size = batch_size
        self.epochs = epochs
        self.verbose = verbose
        self.latent_dim = latent_dim
        self.input_dim = input_dim

        self.model = VAEModule(self.input_dim, self.latent_dim)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-3)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def fit(self, X_train, batch_size=32):
        X_train_tensor = torch.tensor(X_train, dtype=torch.float32).to(self.device)
        train_loader = DataLoader(
            TensorDataset(X_train_tensor), batch_size=64, shuffle=True
        )

        self.model.train()
        for epoch in range(self.epochs):
            total_loss = 0
            for batch in train_loader:
                x_batch = batch[0]
                self.optimizer.zero_grad()
                x_recon, mu, logvar = self.model(x_batch)
                loss = loss_function(x_batch, x_recon, mu, logvar)
                loss.backward()
                self.optimizer.step()
                total_loss += loss.item()
            if self.verbose:
                if epoch % 10 == 0:
                    print(f"Epoch {epoch}, Loss: {total_loss:.2f}")

    def classify(self, X_test, y_test=None):
        self.model.eval()
        # Add this to your classify method
        if len(X_test.shape) == 1:
            X_test = X_test.reshape(1, -1)  # Add batch dimension
        X_test_tensor = torch.tensor(X_test, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            x_test_recon, _, _ = self.model(X_test_tensor)
            recon_error = (
                torch.mean((x_test_recon - X_test_tensor) ** 2, dim=1).cpu().numpy()
            )
            threshold = np.percentile(recon_error, 95)
            y_pred = (recon_error > threshold).astype(int)
        return y_pred

    # def report(self, y_true, y_pred):
    #     print("Classification Report:")
    #     print(
    #         classification_report(
    #             y_true, y_pred, target_names=["Normal", "Anomaly"], zero_division=0
    #         )
    #     )

    def save(self, path):
        torch.save(self.model.state_dict(), path)

    def load(self, path):
        self.model.load_state_dict(torch.load(path, weights_only=True))

    @staticmethod
    def build(**kwargs):
        """ This is a builder method for the VAE types of detectors """
        
        num_metrics = kwargs.get('num_metrics')  # retrieve num_metrics from kwargs
        latent_dim = kwargs.get('ell', 10)  # default latent dimension
        if latent_dim > num_metrics:
            raise ValueError("latent_dim cannot be greater than num_metrics")
        verbose = kwargs.get('verbose', False)  # default verbose

        if num_metrics is None:
            raise ValueError("num_metrics must be provided")
        
        return VAE(num_metrics, latent_dim=latent_dim, verbose=verbose)

if __name__ == "__main__":
    
    import numpy as np
    import torch
    import time

    # Create a fake test dataset
    input_dim = 64  # Example dimension
    n_samples = 1
    X_test = np.random.rand(n_samples, input_dim)
    y_test = np.zeros(n_samples)  # All normal samples for simplicity

    # Initialize the VAE without training
    vae = VAE(input_dim=input_dim)

    # torch.save(dummy_vae.model.state_dict(), dummy_model_path)

    # Load the dummy model
    # vae.load(dummy_model_path)

    # Measure prediction time
    start_time = time.time()
    y_pred = vae.classify(X_test)
    end_time = time.time()

    print(f"Prediction time: {end_time - start_time:.4f} seconds")
    print(f"Samples processed: {X_test.shape}")
    print(f"Time per sample: {(end_time - start_time) / n_samples * 1000:.4f} ms")
    print(f"Predicted anomalies: {sum(y_pred)}")