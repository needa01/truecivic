from prefect_github import GitHubRepository
from prefect.utilities.asyncutils import sync_compatible

github_block = GitHubRepository(
    repository_url="https://github.com/needa01/truecivic",
    reference="main",
)

# Correctly save synchronously
sync_compatible(github_block.save)("truecivic-repo", overwrite=True)