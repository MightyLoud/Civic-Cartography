#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, os, platform, re, subprocess, sys, urllib.request
from pathlib import Path
from importlib import metadata

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/licensing/lic-g5'; OUT.mkdir(parents=True,exist_ok=True)
GEN=Path('/tmp/requirements-ci.generated.lock'); COM=ROOT/'requirements-ci.lock'
NORM=lambda s: re.sub(r'[-_.]+','-',s).lower()
SHA=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def dump(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
def git_files(): return [ROOT/p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
def parse_lock(p):
    rows=[]; cur=None
    if not p.exists(): return rows
    for line in p.read_text().splitlines():
        m=re.match(r'^([A-Za-z0-9_.-]+)==([^\s\\]+)',line)
        if m:
            if cur: rows.append(cur)
            cur={'name':NORM(m.group(1)),'version':m.group(2),'hashes':re.findall(r'--hash=sha256:([0-9a-f]{64})',line)}
        elif cur: cur['hashes']+=re.findall(r'--hash=sha256:([0-9a-f]{64})',line)
    if cur: rows.append(cur)
    for r in rows:r['hashes']=sorted(set(r['hashes']))
    return rows

def gh(url):
    h={'Accept':'application/vnd.github+json','User-Agent':'lic-g5'}
    if os.getenv('GITHUB_TOKEN'):h['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=30) as r:return json.load(r),None
    except Exception as e:return None,str(e)

def actions():
    found={}
    for p in sorted((ROOT/'.github/workflows').glob('*.y*ml')):
        for n,line in enumerate(p.read_text(errors='replace').splitlines(),1):
            m=re.match(r'^\s*uses:\s*["\']?([^"\'\s#]+)',line)
            if m:found.setdefault(m.group(1),[]).append({'path':str(p.relative_to(ROOT)),'line':n})
    out=[]
    for ref,loc in sorted(found.items()):
        row={'reference':ref,'occurrences':loc}
        if ref.startswith('./'):row|={'kind':'local'}
        elif ref.startswith('docker://'):row|={'kind':'docker'}
        elif '@' in ref and len(ref.split('/'))>=2:
            path,tag=ref.rsplit('@',1); owner,repo=path.split('/')[:2]; api=f'https://api.github.com/repos/{owner}/{repo}'
            commit,ce=gh(f'{api}/commits/{tag}'); lic,le=gh(f'{api}/license')
            text=''
            if isinstance(lic,dict) and lic.get('content'):text=base64.b64decode(lic['content']).decode(errors='replace')
            row|={'kind':'external','repository':f'{owner}/{repo}','declared_ref':tag,'ref_is_sha':bool(re.fullmatch(r'[0-9a-fA-F]{40}',tag)),'resolved_sha':commit.get('sha') if isinstance(commit,dict) else None,'resolve_error':ce,'license_spdx':((lic or {}).get('license') or {}).get('spdx_id') if isinstance(lic,dict) else None,'license_sha256':hashlib.sha256(text.encode()).hexdigest() if text else None,'license_error':le}
        else:row|={'kind':'unparsed'}
        out.append(row)
    return out

def installers():
    pats=re.compile(r'python(?:3)?\s+-m\s+pip\s+install|\bpip3?\s+install|apt(?:-get)?\s+install|npm\s+(?:install|ci)|pnpm\s+(?:install|add)|yarn\s+(?:install|add)|\bcurl\b|\bwget\b|git\s+clone|docker\s+pull',re.I)
    out=[]
    for p in git_files():
        try:
            if p.stat().st_size>2_000_000:continue
            lines=p.read_text(errors='replace').splitlines()
        except Exception:continue
        for n,line in enumerate(lines,1):
            if pats.search(line):out.append({'path':str(p.relative_to(ROOT)),'line':n,'text':line.strip()})
    return out

def audit():
    p=OUT/'pip-audit.json'
    if not p.exists():return {'count':None,'items':[],'error':'missing'}
    try:data=json.loads(p.read_text())
    except Exception as e:return {'count':None,'items':[],'error':str(e)}
    deps=data.get('dependencies',data if isinstance(data,list) else []); items=[]
    for d in deps:
        for v in d.get('vulns',[]):items.append({'package':d.get('name'),'version':d.get('version'),**v})
    return {'count':len(items),'items':items}

def main():
    lock=parse_lock(GEN); committed=parse_lock(COM); acts=actions(); inst=installers(); aud=audit()
    direct=[]
    for req_file in ('requirements-dev.txt','requirements-ci.txt'):
      for raw in (ROOT/req_file).read_text().splitlines():
          x=raw.split('#',1)[0].strip()
          if x and not x.startswith('-r '):direct.append(NORM(re.split(r'[<>=!~ ]',x,1)[0]))
    names={r['name'] for r in lock}
    pkgs=json.loads((OUT/'python-licenses.json').read_text()) if (OUT/'python-licenses.json').exists() else []
    package_names={NORM(x.get('Name','')) for x in pkgs}
    checks={
      'generated_lock_exists':GEN.exists(),
      'committed_lock_exists':COM.exists(),
      'lock_matches_generated':GEN.exists() and COM.exists() and SHA(GEN)==SHA(COM),
      'lock_hash_complete':bool(lock) and all(r['hashes'] for r in lock),
      'direct_requirements_covered':set(direct)<=names,
      'python_license_inventory_complete':names<=package_names,
      'workflow_action_inventory_nonempty':bool(acts),
      'external_actions_resolved_and_licensed':all(a.get('kind')!='external' or (a.get('resolved_sha') and a.get('license_spdx') not in (None,'NOASSERTION')) for a in acts),
      'installer_inventory_nonempty':bool(inst),
      'pip_audit_zero_vulnerabilities':aud['count']==0,
      'pytest_passed':os.getenv('PYTEST_EXIT')=='0',
      'yaml_passed':os.getenv('YAML_EXIT')=='0',
      'lock_deterministic':os.getenv('LOCK_EXIT')=='0'}
    passed=all(checks.values())
    env={'python':platform.python_version(),'pip':metadata.version('pip'),'pip-tools':metadata.version('pip-tools'),'pip-audit':metadata.version('pip-audit'),'pip-licenses':metadata.version('pip-licenses')}
    ev={'control_id':'LIC-G5','schema_version':1,'repository':'MightyLoud/Civic-Cartography','commit_sha':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'tree_sha':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=ROOT,text=True).strip(),'github_run_id':os.getenv('GITHUB_RUN_ID'),'environment':env,'requirements_sha256':SHA(ROOT/'requirements-ci.txt'),'generated_lock_sha256':SHA(GEN) if GEN.exists() else None,'committed_lock_sha256':SHA(COM) if COM.exists() else None,'resolved_dependencies':lock,'workflow_actions':acts,'mutable_action_refs':[a['reference'] for a in acts if a.get('kind')=='external' and not a.get('ref_is_sha')],'installer_commands':inst,'vulnerabilities':aud,'checks':checks,'lic_g5_pass':passed,'authority_boundary':{'dependency_licenses_create_root_license':False,'publication_authority':False,'transfer_authority':False,'implementation_authority':False},'reopen_on':['dependency or lock change','workflow action or installer change','new vulnerability','repository drift']}
    dump('workflow-actions.json',acts); dump('installer-inventory.json',inst); dump('lic-g5-evidence.json',ev)
    manifest={p.name:SHA(p) for p in OUT.iterdir() if p.is_file() and p.name!='SHA256SUMS.json'}; dump('SHA256SUMS.json',manifest)
    (OUT/'README.md').write_text('# LIC-G5 Supply-Chain Evidence\n\n'+f"Result: **{'PASS' if passed else 'OPEN / FAIL-CLOSED'}**\n\n"+'\n'.join(f"- [{'x' if v else ' '}] `{k}`" for k,v in checks.items())+'\n\nDependency and action licenses do not create a root Civic-Cartography license.\n')
    print(json.dumps({'pass':passed,'checks':checks},indent=2)); return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
