from prefect_github import GitHubRepository 

github_block = GitHubRepository(
    repository="needa01/truecivic",  # your repo
    reference="main",               # always pull latest main branch
)
github_block.save("truecivic-repo", overwrite=True)

print("GitHub storage block 'truecivic-repo' created successfully!")
