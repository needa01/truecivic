from prefect_github import GitHubRepository 
from prefect.utilities.asyncutils import sync_compatible

github_block = GitHubRepository(
    repository_url="https://github.com/needa01/truecivic.git",  # your repo
    reference="main",               # always pull latest main branch
)

# Correct usage
sync_save = sync_compatible(github_block.save)
sync_save(name="truecivic-repo", overwrite=True)

print("GitHub storage block 'truecivic-repo' created successfully!")
