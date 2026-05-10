"""
GitHub Integration Routes
Allows fetching repositories and branches for the monitor configuration UI.
"""
from flask import Blueprint, request, jsonify
from github import Github, GithubException
import logging

logger = logging.getLogger("morphic.github")
github_bp = Blueprint('github', __name__)

@github_bp.route('/api/github/repos', methods=['POST'])
def get_repos():
    """Fetch repositories for the provided PAT."""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return jsonify({"error": "GitHub token is required"}), 400
            
        gh = Github(token)
        # Fetch up to 100 recent repos to keep it fast
        repos = []
        user = gh.get_user()
        
        # Get user's own repos and repos where they are a member/contributor
        for repo in user.get_repos(sort='pushed', direction='desc'):
            repos.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "owner": repo.owner.login,
                "description": repo.description,
                "url": repo.html_url
            })
            if len(repos) >= 100:
                break
                
        return jsonify({"repos": repos})
        
    except GithubException as e:
        logger.error(f"GitHub error: {e}")
        return jsonify({"error": str(e.data.get('message', 'GitHub API error'))}), e.status
    except Exception as e:
        logger.error(f"Failed to fetch repos: {e}")
        return jsonify({"error": str(e)}), 500

@github_bp.route('/api/github/branches', methods=['POST'])
def get_branches():
    """Fetch branches for a specific repository."""
    try:
        data = request.get_json()
        token = data.get('token')
        repo_full_name = data.get('repo')
        
        if not token or not repo_full_name:
            return jsonify({"error": "Token and repo name are required"}), 400
            
        gh = Github(token)
        repo = gh.get_repo(repo_full_name)
        
        branches = []
        for branch in repo.get_branches():
            branches.append({
                "name": branch.name,
                "protected": branch.protected
            })
            
        return jsonify({"branches": branches})
        
    except GithubException as e:
        logger.error(f"GitHub error: {e}")
        return jsonify({"error": str(e.data.get('message', 'GitHub API error'))}), e.status
    except Exception as e:
        logger.error(f"Failed to fetch branches: {e}")
        return jsonify({"error": str(e)}), 500

def register_github_routes(app):
    """Register the GitHub blueprint."""
    app.register_blueprint(github_bp)
