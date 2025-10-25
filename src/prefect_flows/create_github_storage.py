from prefect_github import GitHubRepository
from prefect.utilities.asyncutils import sync_compatible

# Define the GitHub block
github_block = GitHubRepository(
    repository_url="https://github.com/needa01/truecivic.git",
    reference="main",
)

def create_github_storage_block(block_name: str = "truecivic-repo", overwrite: bool = True):
    """
    Safely create the GitHubRepository block synchronously.
    """
    try:
        sync_save = sync_compatible(github_block.save)
        # Call the wrapped save function
        sync_save(name=block_name, overwrite=overwrite)
        print(f"GitHub storage block '{block_name}' created successfully!")
    except Exception as e:
        print(f"GitHub storage block creation failed: {e}")

# ONLY create block if this script is run directly
if __name__ == "__main__":
    create_github_storage_block()
