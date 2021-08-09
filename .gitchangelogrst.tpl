% if data["title"]:
${data["title"]}
\n
${"=" * len(data["title"])}


% endif
% for version in data["versions"]:
<%
title = "%vs (%s)" % (version["tag"], version["date"]) if version["tag"] else opts["unreleased_version_label"]

nb_sections = len(version["sections"])
%>${title}
${"-" * len(title)}
% for section in version["sections"]:
% if not (section["label"] == "Other" and nb_sections == 1):

${section["label"]}
${"~" * len(section["label"])}
% endif
% for commit in section["commits"]:
<% c = commit["subject"]
if commit["body"]:
  c += "\n" + commit["body"].replace("\n\n", "\n")
entry = indent(c, first="- ").strip()
%>${entry}
% endfor
% endfor

% endfor
