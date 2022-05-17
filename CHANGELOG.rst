Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a
Changelog <http://keepachangelog.com/en/1.0.0/>`__ and this project
adheres to `Semantic Versioning <http://semver.org/spec/v2.0.0.html>`__.

v1.5.2 (2022-05-17)
-------------------

Changes
~~~~~~~
- When an exit fail to exit, check CC.
  before selecting other exits as helpers.
  In #40136 we forgot to consider the corner case in #40041, discovered
  thanks to analysis#36.
  This was causing that sometimes a CC circuit was built when
  bwscanner_cc wasn't equal or greater than 1 or the other way around.
  We didn't realize about this cause this part of the code is very
  confusing. To don't make it even more confusing, i've changed the
  internal API:

  - `select_helper_candidates`: split function into one to select the
    helper candidates, knowing whether to use the relay as exit or not
    and other function `use_relay_as_entry` to decide whether to use the
    relay as entry or not checking CC params.
    Also pass a new arg `relay_as_entry`.
  - `create_path_relay`: remove not used `cb` arg, add `candidates` arg
    to stop having to select them again later on. Move the no
    `candidates` condition here instead of checking it in
    `pick_ideal_second_hop`.
  - `_pick_ideal_second_hope: remove unneeded `dest` and `cont arguments,
    rename `is_exit` to `helper_is_exit`. Use the candidates instead of
    selecting them again.
  - `measure_relay`: in the case an exit fails to exit, select the
    candidates knowing that they have to be exits and checking CC.
  - `only_relays_with_bandwidth`: remove unneeded arg `controller` so
    that there is no need to pass it through several functions.

  Closes #40138
- Consensus weight fraction of CC exits.
  Closes #40139
- Scanner: check `bwscanner_cc` and `FlowCtrl`
  before measuring an exit as exit.
  Closes #40136

Fix
~~~
- Doc: changelog indentation and new lines
- Relaylist: Comment too verbose logs.
  And log consensus params items instead of just keys.

v1.5.1 (2022-05-10)
-------------------

Changes
~~~~~~~
- Change `cc_alg` and `bwscanner_cc` values to int.
  Because consensus parameters are strings in stem.
  Closes #40134.

v1.5.0 (2022-04-26)
-------------------

New
~~~
- Choose exits that implement congestion control.
  and create methods to check that the consensus implements congestion
  control.
  Closes #40125

Changes
~~~~~~~
- Add subcommand to show exits with 2 in FlowCtrl.
  Closes #40132

Fix
~~~
- Update authors.

v1.4.0 (2022-02-14)
-------------------

Changes
~~~~~~~
- Remove support for Python 3.6.
  because it's already EOL. Also update dates other python releases.
- Config: Stop printing which config file is used.
  sbws doesn't use default logging configuration until it tries to read
  configuration files. However it prints to stdout which configuration
  file is being used before that.
  If an sbws' operator wish to only receive emails on warnings, they'll
  still receive emails because of the print line. Therefore stop printing
  before configuring logging.
  Closes #40110.
- Clarify stats and units in the logs.
  to make them less confusing.
  Closes #40109.
- Create home directory after reading config.
  Otherwise it'd create a `.sbws` directory even when it's run as
  a supervised service.
  Closes #40108

Fix
~~~
- Maint: Require mako library to create release.
- Meta: Upgrade stem version.
  that was long ago released
- CI: Update comments about tor releases.
  Remove comment about tor 0.3.5, already EOL and update dates other tor
  releases become stable or EOL.
  No need to remove tests with tor 0.3.5, since there wasn't anymore.
- CI: Stop allowing python 3.10 to fail.
  Also:
  - add Python 3.10 as supported version.
  - target Python 3.10 in black
- CI: Update Python default version to 3.9.
  Also:
  - remove redundant image variable
  - build docs with python 3.9 too
  - Add python 3.9 as target-version for black
- Style: Remove spaces around power operators.
  if both operands are simple. To make CI tests pass with new black
  version 22.1 (#2726).
  Closes #40123
- Clarify log level to use for alerts.
  If a bwauth operator wish to receive (email) alerts, it might be more
  convenient to set the log level to error.
  Closes #40121
- V3bwfile: Lower log level about no observed bw.
  Because it might happen due fetching "early", "useless" descriptors or
  non running relays, so that there aren't too many warnings.
  Closes #40116.
- V3bwfile: Clarify percent warning.
  about the difference between the sum of the last consensus weight and
  the sum of the reported weight in the just generated Bandwidth File.
  Otherwise, when looking at the warnings only, it's not explained what
  the percentage is about.
  Closes #40115
- Improve coverage timestamps.py.
- Correct metadata urls and files.
  The readme a and license files changed to restructured text and the
  urls were missing `https`.
  Also add maintainer and contact metadata and remove travis link since
  travis is not being used anymore.
  Closes #40100.
- CI: tor-nightly-0.3.5.x-bullseye release is empty.
  and it is not used by any bwauth.
  Closes #40114.
- CI: Replace Debian package name.
  that changed from master to main.
- Comment about keep-alive timeout.
  in the Web server.
  Closes #40112
- Make CDN more optional.
- CI: update python versions.
  because bullseye is the new Debian stable, has by default python3.9
  amd tests using buster dependencies fail.
  Closes #40099.

Other
~~~~~
- Remove userquery code.
- Change default country to AA for [scanner]
  SN was set as default value instead of AA
  according to ISO 3166, SN refers to Senegal.
- Update scanner.country's comment.
  - sbws.example.ini described destination's country inside of scanner's
- Improvements and being inline with pep8.
  As juga suggested in the commits, I've done.
  I tried to figure out another way instead of manually defining the value but couldn't figure it out
- Line length was too long.
  line 64 was too long
- Changed variables to PEP 8 standard.
  I didn't see the link https://tpo.pages.torproject.net/network-health/sbws/contributing.html#code-style
  changed the variables
- Heartbeat coverage improvement.
  This should increase the coverage to 100% and should be passing the tests/commands when running tox
- Heartbeat coverage improvement.
  This should increase the coverage to 100% and should be passing the tests/commands when running tox
  Changed variables to PEP 8 standard
  I didn't see the link https://tpo.pages.torproject.net/network-health/sbws/contributing.html#code-style
  changed the variables
  line length was too long
  line 64 was too long
  improvements and being inline with pep8
  As juga suggested in the commits, I've done.
  I tried to figure out another way instead of manually defining the value but couldn't figure it out

v1.3.0 (2021-08-09)
-------------------

Changes
~~~~~~~
- Split dumpstacks into handle_sigint.
  stop exiting when there's a possible exception that makes sbws stalled
  and instead just dump the stack. Additionally, call pdb on sigint.
- Scanner: Move to concurrent.futures.
  away from multiprocessing, because it looks like we hit python bug
  22393, in which the pool hangs forever when a worker process dies.
  We don't know the reason why a worker process might due, maybe oom.
  See https://stackoverflow.com/questions/65115092/occasional-deadlock-in-multiprocessing-pool,
  We also run into several other issues in the past with multiprocessing.
  Concurrent.futures has a simpler API and is more modern.
  Closes #40092.
- V3bwfile: Stop scaling with consensus weight.
  because when the observed bandwidth is higher than the consensus (for
  example when the relay is new or was some time down), it's limited by
  the previous consensus, not allowing it to grow.
  Since the size of the data to download depends also on the consensus
  weight, this results on lower measured bandwidth too.
  Closes #40091.

Fix
~~~
- Add the tag `v` in gitchangelog template.
- Add missing date to last release.
- Recommend system timezone in UTC.
- Tests: Consensus bandwidth might not be 0.
  Since tor version 0.4.7.0-alpha-dev with #40337 patch, chutney relays
  notice bandwidth changes.
- Scanner: Rename functions.
  to more appropriate names, after switching to concurrent. futures.
- Typos.
- CI: Install tor specifying release.
  instead of version, so that it's more clear which version is being installed.
- CI: Really test tor stable.
  since the default tor with deb.tpo repository is master
- CI: Really test tor 0.4.6.
  since master is the default and add test for master.
- CI: Change indentation to 2 chars.
- Scanner: Increase time getting measurements.

  - Increase the time waiting for the last measurements queued, to avoid
    canceling unfinished measurements and gc maybe not releasing thread
    variables
  - Use the already declared global pool instead of passing it by args
  - Log more information when the last measuremetns timeout
- Reformat docstrings for black.
  To pass tox tests.
  This seems to have changed in black from version 20.8b1 to 21.4b2.
- Update python version for rtfd.io.
- CI: Build docs automatically in Gitlab.
  also replace the links to Read the Docs to pages.torproject.net
  and add redirect to it.

v1.2.0 (2021-04-14)
-------------------

New
~~~
- Docs: Include script on how to release.
- Scripts: Add script to help new releases.
- Add gitchangelog template.
- Add gitchangelog configuration file.
- Docs: Add bwauths list image.
- Relaylist: Keep relays not in last consensus.
  Keep the relays that are not in the the last consensus, but are not
  "old" yet.
- Util: Add function to know if timestamp is old.
  Part of #30727.

Changes
~~~~~~~
- Stem: Set default torrc options.
  when connecting to an external tor and they are not already set.
- Generate, cleanup: Use 28 days of measurements.
  When generating the Bandwidth File as Torflow, use 28 days of past raw
  measurements instead of 5, by default.
  Also keep the raw measurements for that long before compressing or
  deleting them.
  And stop checking whether the compression and delete
  periods are valid, without checking defaults first and based on
  arbitrary values.
- Stem: Add function to connect or start tor.
  Move initialization via existing socket to this new function and start
  tor only when it fails.
- Stem, scanner: Change args initializing controller.
  to check whether the external control port configuration is set.
  There is no need to assert all argument options nor to return the error.
- Config: Add option to connect to external tor.
  via control port.
- Circuitbuilder: Remove not used attributes.
  and make argument optional.
- Circuitbuilder: Simplify building circuit.
  Since sbws is only building 2 hop paths, there is no need to add random
  relays to the path, or convert back and forth between fingerprint and
  ``Relay`` objects.
  This will eliminate the circuit errors:
  - Tor seems to no longer think XXX is a relay
  - Can not build a circuit, no path.
  - Can not build a circuit with the current relays.
  If a relay is not longer running when attempting to build the circuit,
  it will probably fail with one of the other circuit errors: TIMEOUT,
  DESTROYED or CHANNEL_CLOSED.
- Scanner: Stop storing recent_measurement_attempt.
  because it stores a timestamp for each attempt, which makes state.dat
  grow thousand of lines (json).
  Closes #40023, #40020
- V3bwfile: Exclude relays without observed bw.
  and without consensus bw from scaling.
  Part of #33871, closes #33831.
- V3bwfile: Percentage difference with consensus.
- V3bwfile: Calculate hlimit from scaled sum bw.
  instead of bw before scaling.
  Tests have finally correct value.
  For 1 result, only when the cap is 1, the value will be equal to the
  rounded bw because the cap does not limit it.
- V3bwfile: Obtain consensus values from last consensus.
- V3bwfile: Round scaled bandwidth after capping.
  Make tests pass because the high limit change the expected values,
  but the final value still needs to be fixed.
- V3bwfile: Change logic obtaining min bandwidth.
  Take either the consenus bandwidth or the descriptor bandwidth if
  one of them is missing, do not scale when both are missing and
  ignore descriptor average and burst when they are missing.
- V3bwfile: Scale relays missing descriptor bws.
  Scale relays without average or observed bandwidth.
  Later it will be check what to do if their values are None or 0
- V3bwfile: Stop making mean minimum 1.
- V3bwfile: Calculate filtered bandwidth.
  for each relay, calculate the filtered mean for all relays and
  calculate the filtered ratio for each relay.
- Scaling: Add filtered bandwidth function.
  to calculate the filtered bandwidth for each relay.
- Bwfile: Test KeyValues in a bandwidth file.
  Added:
  - library to check whether the KeyValues make sense
  - test an example bandwidth file
  - a command to check an arbitrary bandwidth file
  Finally, doing something with all these KeyValues!
  (Quarantine day 7th)
- V3bwfile: Count recent relay's monitoring numbers.
  using timestamps class.
  Also add one more result to the tests data and change the
  test accordingly.
- Tests: Remove `_count` from attr.
- Resultdump: Add missing attrs to errors.
- Resultdump: Remove `_count` from attributes.
  Tests wont' pass with this commit, they'll be fixed in the next commits
- Relayprioritizer: Count priorities with timestamps.
  in RelayPrioritizer:

  - Rename recent_priority_list_count to recent_priority_list when
    there is no counting
  - Rename recent_priority_relay_count to recent_priority_relay
    when there is no counting
  - Use the timestamps class to manage/count priority lists/relays
- Relaylist: Count measurements with timestamps.
  in RelayList:

  - Rename recent_measurement_attempt_count to recent_measurement_attempt when
    there is no counting
  - Use the timestamps class to manage/count measurement attempts
- Relaylist, v3bwfile: Count consensus with timestamps.
  in RelayList:

  - Rename consensus_timestamps to recent_consensus
  - Rename recent_consensus_count to recent_consensus when there is
    no counting
  - Use the timestamps class to manage/count consensuses
  - Remove method not needed anymore
- V3bwfile: Convert datetime to str.
- Resultdump: Use custom json encoder/decoder.
- State: Encode/decode datetimes.
- Json: Create custom JSON encoder/decoder.
  to be able to serialize/deserialize datetime in the state file.
- Timestamps: Add module to manage datetime sequences.
- State: Add method to count list values.

Fix
~~~
- Clarify release script dependencies.
- Use rst changelog template.
  and put in the same entry commit subject and body removing new lines.
- Correct network stream and filtered bw.
  because Torflow is not using them by relay type.
- V3bwfile: network means without relay type.
  This reverts commit fc3d3b992ada601a6255f8a6889179abd4b7e55e and partially
  reverts a82c26184097bea3ca405ae19773de7c4354a541.
  It was a mistake to think torflow was using the means by relay type,
  it actually sets the same networks means for all relay types.
  Closes #40080.
- Semi-automatic correction of typos.
  Closes #33599.
- Tests: Add codespell configuration.
- Tests: Additional security tests.
- CI: Use all tox environments for python 3.8.
- 2nd round of automatic format.
  black insists to keep one long line and flake complain, therefore make
  flake to ignore it.
- Flake8 errors.
- Reorder imports with isort.
- Reformat all with black.
- Move to declarative setup.cfg.
  Also:
  - Update versioneer
  - And include other source distribution files in MANIFEST.in
  - Add project URLs
  - Add formatter and linter dependencies and configurations.
  - tox: Remove travis, fix python environments
  - tox: Remove extra coverage options and add them in .coveragerc.
- Indent by default to 2 except python files.
  also uncomment final newline. Can be commented again in case it fails
- V3bwfile: network means by relay type.
  Calculate network stream and filtered bandwidth averages per relay
  type, to obtain bandwidth weights the same way as Torflow.
  Closes #40059.
- Scaling: Return mean if no bw >= mean.
- Scaling: Stop returning 1 as the means minima.
  since they are used as the numerator when calculating the ratio and the
  rounding already returns a minimum of 1.
- Scaling: Return if there are no measurements.
  it should not be the case because the measurements come from
  successful results, but otherwise it'd throw an exception.
- Tests: Add bw filtered from results.
- Scaling: round bandwidth filtered.
  because Torflow does it.
- Scanner: Return from measure if no helper.
  After refactoring in #40041, it was forgotten to return the error in
  the case a helper was not found, what can happen in test networks.
  Closes #40065.
- Tests: debug log for tests by default.
  and fix test that didn't consider that there might be other logs from
  other threads.
  Closes #33797.
- Scanner: Log times kept.
  not only the times that are not kept.
  Closes #40060
- CI: Temporal workaround for #40072.
- Relalist: Use the consensus timestamp.
  to the relay consensus timestamps list, so that it can be
  tested it was in a concrete consensus.
- CI: Exit from integration script.
  when any of the commands fail.
- CI: Update Python versions.
  Closes #40055.
- CI: Update tor versions.
- System physical requirements.
  After fixing #40017, the datadir files are compressed after 29 days and
  deleted after 57. However the total used disk space is less than 3G,
  leaving 3G as precaution.
  Closes #40044.
- Scanner: Return from measure if no helper.
  After refactoring in #40041, it was forgotten to return the error in
  the case a helper was not found, what can happen in test networks.
  Closes #40065.
- Update differences Torflow/sbws.
  Closes #40056
- Reorganize Torflow aggregation.
  - reorganize sections
  - add diagrams and links
  - add pseudocode
  - remove math
  - correct statements
  So that it's more accurate and easier to understand.
- Docs: Rename section, add diagrams.
- Separate Torflow/sbws differences.
  into a new file.
- Add target to call plantuml.
  and generate .svg from .puml files.
  Do not add to the html target since the generated svg images are
  not deterministic and will change every time `plantuml` is call.
- Separate how scanner and generator work.
  in different files and link to each other.
- Add missing new lines.
- CI: Make wget quiet.
  to avoid many lines of non useful text the CI.
- Scanner: Rm condition assigning helper.
- Scanner: Move as_entry/as_exit into one function.
  since they're similar code
- Scanner: remove relay to measure as helper.
- Scanner: log exit policy when stream fails.
- Relaylist: Remove duplicated can exit methods.
  After refactoring and making clear when we were using exit(s) that can
  exit to all public IPs (and a port) or only some, refactor them
  removing the duplicated code and adding the `strict` argument.
- Add relay measure activity diagram.
- Scanner: extract method on circuit error.
  At some point all possible errors should be exceptions.
- Scanner: extract method for not helper case.
- Scanner: extract method to create paths.
  because `measure_relay` method is too long, confusing and we have had
  several bugs in this part of the code.
- Relaylist: Add methods to obtain exits that.
  can exit to some IPs.
  To use them in the cases it will be more convenient.
- Relaylist: rename exits_not_bad_allowing_port.
  see previous commit
- Relaylist: rename is_exit_not_bad_allowing_port.
  see previous commit
- Relaylist: rename can_exit_to_port.
  to can_exit_to_port_all_ips, because it's using `strict`, which means
  that it allows to exit to all IPs.
  It seems more convenient to try first with exits that allow to
  exit to some IPs and only try a second time if that fails, because
  there are more.
- Resultdump: Check that the error has a circuit.
  Because if the error is not a circuit error, it does not have that
  attribute.
- Tests: Run integration tests with chutney.
  and adapt the tests to pass.
  \o/
- Add chutney configuration.
  and scripts to run the integration tests with chutney.
  It does not replace yet the way integration tests are run.
- Stem: Move torrc option that does not depend on config.
  It seems we forgot this option when refactoring in #28738.
- Stem: Remove torrc option that is the default.
  to avoid conflict when comparing the options that should be set and the
  ones are set, since the SocksPort will be differently in chutney.
- Resultdump: Log if relay was measured as exit.
  or entry.
  Closes #40048
- Relaylist: Stop measuring relays not in the consenus.
  as this might cause many circuit errors.
  They're already added to the generator.
  Also adapt the number in test_init_relays.
- Sphinx warnings when creating documentation.
  This should give us at least a clean html, text, and man build
  experience.
  Closes #40036.
- Add forgotten image from consensus health.
  It was referenced by 6e6a8f3ba534cbd93b830fe3ffd5ce40abe8e77d. Since that
  image was wrong, created a new screenshot from the current "past 90
  days" at consensus-health.tpo.
- Stem: Add possible exception cause.
- Stem: Remove unused code.
- Stem: Exit on failure connecting to control port.
  because when trying to connect to an external tor (chutney), it does
  not make sense to start own tor.
  Also log how the connection has been made.
- Update values in config_tor.rst + clean-up.
  Closes #40035.
- Update default values in man_sbws.ini.rst.
  Closes #40034.
- Clean up config.rst.
  Closes #40033.
- Scanner: Retry to measure exit as exit.
  if it fails to be measured as entry.
  Mayb closes: #40029.
- Relaylist: Comment on IPv6 exit policy.
  that could be also checked, increasing the chances that the exit can
  exit to our Web servers.
  But if it could not, then we need to retry to measure it as 1st hop.
- Config: Increment circuit build timeout.
  setting it to the default, 60secs.
  Since many relays fail to be measured cause of circuit timeout.
  Maybe closes #40029.
- Bump bandwidth file version to 1.5.0.
  after removing KeyValue recent_measurement_attempt_count in #40023.
  Changed also torspec, issue #20.
- V3bwfile: Tor version added in bandwidth v1.4.0.
  since, by mistake, the bandwidth file version here was never updated
  to v1.5.0.
  This patch only changes the constants names, but logic remains the same.
  Related to torspec#35.
- Add the bwauths timeline wiki.
  Closes #40013.
- Add bwauthealth tool.
- Add consensus health page.
  about bwauths measured relays.
- Move consensus weight to top.
  and explain what to check.
- V3bwfile: Take all measurements when IP changes.
  Previously, when a relay changes IP, only the measurements with the
  last IP were considered.
  Relays with dynamic IP could get unmeasured that way.
  Now, all the measurements are considered.
- V3bwfile: Avoid statistics without data.
  If mean or median argument is empty, they throw an exception.
  This can happen when the scanner has stopped and the result is
  stored as successful without any downloads.
- No need to use Travis anymore.
- Clarify branch to use when contributing.
- Maint: Fix linter error after merging #29294.
- Tests: Stop converting boolean key to int.
  Conversion only happens when parsing a bandwidth file in the
  integration tests.
- Relaylist: filter out private networks.
  when checking exit policies to know whether an exit can exit to a port.
- Update authors.
- Replace docs links from Github to Gitlab.
- Update reviewers.
- Replace Github review process to Gitlab.
  Replace also Github terminology to Gitlab.
- Replace Trac, ticket by Gitlab, issue.
- Replace links from Trac to Gitlab.
- Start using release script later.
  Change the version from which the release script is used.
  Also explain the prefixes used in the commits.
  Closes #29294
- Scripts: Clarify the scope of the script.
  it should not take more effort than solving self-sbws issues.
- Scripts: Reformat sentence.
- Scripts: Stop bumping to next prerelease version.
  since it is now managed automatically by versioneer.
  Instead, suggest creating a "next" maintenance branch.
  But stop using `-` and `.` characters in it, to type it faster, since
  most of the new branches will be based on it.
- Scripts: Stop releasing from -dev0 version.
  since now sbws version is calculated from last release tag.
- Scripts: Stop changing version in __init__
  Since it is now done by `versioneer`.
- Scripts: Change Github by Gitlab.
  releases can live now in gitlab.tpo, instead of github.com and
  there is no need to check them since Gitlab is FLOSS and gitlab.tpo is
  hosted by Tor Project.
  Also, stop assuming which is the current branch and remote and do not
  push. Instead guide the maintainer to do it.
- CI: Add .gitlab-ci.yml to run tests in Gitlab.
- Relaylist: Check exit to all domains/ips.
  When an exit policy allows to exit only to some subnet, it is not
  enough to check that it can exit to a port, since it can, but it might
  not be able to exit to the domain/ip of the sbws Web servers.
  To ensure that without having to check whether it can exit to a
  specific domain/ip, we can query the exit policy with `strict`.
  Closes #40006. Bugfix v1.0.3.
- V3bwfile: Count relay priority lists.
  and measurement attempts from all the results.
  Until they get properly updated.
  Also change dates in tests, so that timestamps are counted correctly
- Recomment maint-1.1 for production.
- Recommend using a CDN,
  add link to it and rephrase some sentences.
- Increase RAM required.
  ahem, because of all json it has to manage in memory.
- Recommend pip only for development.
  or testing and add links.
- Update supported Python versions.
- Comment on Debian/Ubuntu releases.
  because sometimes the package might not be in Debian stable or testing
  and we are not checking Ubuntu releases.
- Tests: Remove all the `\t` in torrc files.
  at the beginning of the line and in empty lines. They are not needed.
- Tests: Create new authority keys.
  because they expired.
  They will expire again in a year.
  Implementing #33150 and using chutney would avoid to update keys.
  Closes #34394.
- V3bwfile: linter error with new flake version.
- Add differences between Torflow and sbws.
  Closes #33871.
- Update/clarify Torflow aggregation.
- Docs: Remove unneeded linter exception.
- Docs: Move torflow scaling docstring to docs.
  so that it has its own page as it is too long as docstring and is
  harder to write latex with the docstring syntax.
- Unrelated linter error.
- V3bwfile: Remove unneeded minimum 1.
  since rounding already returns 1 as minimum.
- V3bwfile: Use cap argument to clip scaled bw.
  Make test pass, though the value is not correct since it needs to be
  rounded after clipping
- V3bwfile: cap is never None.
- V3bwfile: Warn about None bandwidth values.
  since they are probably due a bug.
- Check that log prints a number.
  and not a list of timestamps.
- Assert that caplog messages were found.
- Explain changes in the previous commits.
- Tests: Check the files generated in test net.
  Test that the results, state and bandwidth file generated by running
  the scanner and the generator in the test network are correct.
- Tests: Add tests loading results.
  in ResultDump and incrementing relay's monitoring KeyValues.
- Tests: Add results incrementing relays'
  monitoring KeyValues.
- V3bwfile: Stop calculating failures with 0 attempts.
- Relaylist: Count recent relay's monitoring numbers.
  using timestamps class.
  Additionally:
  - fix: relayprioritizer: Replace call relay priority
  - fix: scanner: Replace call relay measurement attempt
- State: Let json manage data types.
  Since state uses json and json will raise an error when it can't
  decode/encode some datatype.
- State: Read file before setting key.
  Otherwise, if other instance of state set a key, it's lost by the
  current instance.
  Bugfix v0.7.0.
- Tests: Test state file consistency.
  Test that two different instances of state don't overwrite each other.
  This test don't past in this commit, will pass in the next bugfix.
  Bugfix v0.7.0, which claimed 100% test coverage on state.
- Tests: linter error cause missing nl.
- Relaylist: Update relay status before consensus.
  Update relay status before updating the consensus timestamps
  Timestamps that are not old yet were getting removed because the
  document.valid_after timestamp was still the one from the previous
  consensus.
  Closes #33570.
- Tests: Test the number of consensus in Relay.
  This test does not pass in this commit, but in the next bugfix.
- Relaylist: Use is_old fn removing consensus.
  since the logic is the same and the there were two bugfixes on the
  same logic.
- Relaylist: Use seconds removing consensuses.
  by default days is passed to timedelta, what was making the oldest
  date be thousands of days in the past.
  Bugfix 1.1.0.
- Tests: Add relaylist test.
  Tests don't pass in this commit, they're fixed in the next commits.
- Tests: Add mocked controller fixture.
  to be able to unit test all the code that needs a controller.
- Tests: Add test for remove old consensus ts.
  Tests don't pass in this commit, it's fixed in the next commits.
- Timestamp: measurements period is in seconds.
  by default days is passed to timedelta, what was making the oldest
  date be thousands of days in the past.
- Timestamp: Old timestamps are minor than older.
  Old timestamps are minor than the older date, not major.
- Relaylist: Stop passing argument to self.is_old.
- Tests: Add test timestamp.is_old.
  The tests don't pass in this commit, it's fixed in the next ones.
- V3bwfile: Reformat to don't get flake8 errors.
  Part of #30196
- V3bwfile: Move keys to correct constant.
  Part of #30196.
- V3bwfile: Add comment about bwlines v1.3.
  Part of #30196.
- V3bwfile: Add tor_version KeyValue.

  - Create new KeyValues constants for the new v1.5.0 KeyValues
  - Instantiate State in Header.from_results so that there is no need
    to create new methods for all the header KeyValues that are read
    from the state file
  - Add tor_version to the kwargs to initialize the Header
  - Write tor_version in the state file when the scanner is started
- V3bwfile: Add constant for ordered key/values.
  to build the list of all keys from it and ensure no key is missing.
- V3bwfile: Reformat to don't get flake8 errors.
  After the automatic constants renaming, fix the flake8 errors by
  reformatting automatically with `black`, only the lines that had
  errors.
  Part of #30196
- Document why ersioneer to obtain version.
- Add at build time the git revion to version.
  Instead of having a hardcoded version, calculate the version at build
  time making use of `git describe --tags --dirty --always`.
  This way, even if the program is not running from inside a git
  repository it still can know which was the git revision from the
  source it was installed from.
  If the program is launched from a path that is a git repository, it
  does not gives the git revision of that other repository.
  If's also able to get the version when installed from a tarball.
  It does not add the git revision when it's being install from a git
  tag.
  `versioneer` external program is only needed the first time, because
  it copies itself into the repository. So it does not add an external
  dependency.
  There're no changes needed to the `--version` cli argument nor to the
  code that generates the bandwidth file, since they both use the
  variable `__version__`.
  The version previous to this commit was `1.1.1-dev0`, after
  this commit, it becomes `1.1.0+xx.gyyyyyyyy`, ie. xx commits after
  `1.1.0` plus the git short hash (yyyyyyyy).
- Tests: Test maximum retry delta in destination.
- Destination: Replace constant name.
  to make it consistent with others and shorter.
  Part of #33033.
- Destination: Set maximum to retry a destination.
  otherwise the time to retry a destination could increase too much,
  as it's being multiplied by 2, and a destination would not recover.
  Patch submitted by tom.
- Relaylist: linter error after after merge.
  Fix linter error after merging #30733 and #30727.
- CI: Cache pip, run tox stats after success.
  and do not require sudo.
- CI: Test all supported python versions.
  As in chutney and stem:
  - Test all supported python versions
  - Test all supported tor versions
  Differences between chutney, stem and sbws:
  - in sbws we run directly, not an script that calls tox
  - we're not using chutney for integration tests (yet) and therefore we're not testing it with different networks
  - we don't have shellcheck tests
  - we don't support osx nor windows
- Relaylist: Update the relays' descriptors.
  when fetching new consensuses.
  Part of #30733.
- Globals: Fetch descriptors early.
  and useless descriptors, so that sbws detect early changes in the relay
  descriptors and continue downloading them even when Tor is idle.

Other
~~~~~
- Wip: rm me, temporally change release url.
  to personal fork, to test the release process
- Fixup! minor: Change info logs to debug or warning.
- Major: Change default log level to info.
  also change formatting to show thread.
- Minor: Change log warning to info or debug.
  when it contains sensitive information.
- Minor: Change info logs to debug or warning.
  when they contain sensitive information, eg. Web server or are too
  verbose for the debug level.
  Also add log to indicate when the main loop is actually started.
- Revert "fix: stem: Remove torrc option that is the default"
  This reverts commit 15da07d6a447d8310354124f6020b4cf74b75488.
  Because it's not the default. No additional changes are needed in the
  tests.
  Closes #40064.
- Minor: scanner: Change logic creating the path.
  When the relay is not an exit, instead of choosing exits that can
  exit to all IPs, try with exits that can exit to some IPs, since the
  relay will be measured again with a different exit in other loop.
  When the relay is an exit, instead of ensuring it can exit all IPs, try
  using it as exit if it can exit to some IPs.
  If it fails connecting to the Web server, then try a 2nd time using it
  as entry to avoid that it will fail in all loops if there is only one
  Web server, cause it will be used again as an exit.
  Also, the helper exits don't need to be able to exit all IPs. When a
  helper exit fails to exit (maybe cause it can not exit to the Web
  sever IP), it's not a problem cause in a next loop other exit will be
  chosen.
  This change of logic also solves the bug where non exits were being
  used as exits, because we were trying to measure again a relay that
  was used as entry, because it could not exit all IPs, which includes
  also the non exits.
- Minor: scanner: move checking helper to methods.
  `helper` variable is only used to return error, therefore move it to
  the methods that create the path and return the error there.
  `our_nick` is not useful for the log, since it is always the same, but
  not removing it here.
- Vote on the relays with few or close measurements.
  to vote on approximately the same numbers of relays as Torflow.
  Torflow does not exclude relays with few or close measurements, though
  it is possible that because of the way it measures, there are no few
  or close measurements.
  Closes #34393
- Doc: fix: Update sbws availabity in OS and links.
- Bug 33009: Require minimum bandwidth for second hop.
- Use freeze_time() in other parts of our tests, too.
  When using `_relays_with_flags()` and similar methods it's possible
  that tests start to hang without time freezing. See bug 33748 for more
  details. We work around this by providing the necessary `freeze_time()`
  calls meanwhile.
- Bug 33600: `max_pending_results` is not directly used in `main_loop`
- Fixup! fix: CI: Test all supported python versions.
- Relaylist: stop using the current time when a consensus is downloaded twice.
  Instead:
  * use the consensus valid-after time, or
  * use the supplied timestamp, or
  * warn and use the current time.
  This should fix the occasional CI failure, when the current time is 1 second
  later than the test consensus time. (Or it should warn, and we can fix the
  test code.)
  Fixes bug 30909; bugfix on 1.1.0.
- V3bwfile: skip relay results when required bandwidths are missing.
  Fixes bug 30747; bugfix on 1.1.0.
- Bump to version 1.1.1-dev0.

v1.1.0 (2019-03-27)
-------------------

New
~~~

- V3bwfile: Report excluded relays.
  Closes: #28565.
- V3bwfile: Add time to report half network.
  Closes: #28983
- Destination: Recover destination when it failed.
  Closes: #29589.
- V3bwfile: Report relays that fail to be measured.
  Closes: #28567.
- V3bwfile: Report relays that are not measured measured.
  Closes: #28566
- V3bwfile: Add KeyValues to monitor relays.
  Closes: #29591.
- Docs: document that authorities are not measured.
  Closes: #29722
- Scanner: Warn when there is no progress.
  Closes: #28652

Fix
~~~
- v3bwfile: Report relays even when they don't reach a minimum number.
  Closes: #29853.
- Minor fixes. Closes #29891.
- Relaylist: Convert consensus bandwidth to bytes.


v1.0.5 (2019-03-06)
-------------------

- Release v1.0.5.
  this time with the correct version

v1.0.4 (2019-03-06)
-------------------

- Release v1.0.4.
  because there was a commit missing between `1.0.3` and `1.0.4-dev0`
  and what is released as `1.0.3` has version `1.0.4-dev0` and it
  can not be fixed now.

v1.0.3 (2019-02-28)
-------------------

Fixed
~~~~~~

- scanner: check that ResultDump queue is not full
  Fixes bug #28866. Bugfix v0.1.0.
- config: set stdout log level to cli argument. Closes: #29199
- cleanup: Use getpath to get configuration paths. Bugfix v0.7.0.
- destination: stop running twice usability tests.
  Fixes bug #28897. Bugfix v0.3.0
- globals, stem: explain where torrc options are.
  Fixes bug #28646. Bugfix v0.4.0
- stem: disable pad connections. Fixes bug 28692. Bugfix v0.4.0
- generate: Load all results, including error ones.
  Closes #29568. Bugfix v0.4.0 (line introduced in v0.1.0).
- relayprioritizer: Stop prioritizing relays that tend to fail.
  Fixes bug #28868. Bugfix v0.1.0
- circuitbuilder: Stop building the circuit 3 times.
  Fixes bug #29295. Bugfix v0.1.0.
- docs: add verify option to man and example.
  Closes bug #28788. Bugfix v0.4.0.
- CI: run scanner using the test network. Fixes bug #28933. Bugfix v0.1.0.
- scanner: catch SIGINT in the main loop. Fixes bug #28869. Bugfix v0.1.0.
- Stop including tests network as binary blob. Fixes bug #28590. Bugfix v0.4.0.
- relaylist: remove assertions that fail measurement.
  Closes #28870. Bugfix v0.4.0
- config: Use configuration provided as argument.
  Fixes bug #28724. Bugfix v0.7.0.
- stem: parse torrc options that are only a key.
  Fixes bug #28715. Bugfix v0.1.1
- stem: Stop merging multiple torrc options with the same name.
  Fixes bug #28738. Bugfix v0.1.1
- docs: add note about syslog when running systemd.
  Closes bug #28761. Bugfix v0.6.0
- CI: include deb.torproject.org key.
  Closes #28922. Bugfix v1.0.3-dev0
- config: stop allowing http servers without tls.
  Fixes bug #28789. Bugfix v0.2.0.
- Make info level logs more clear and consistent.
  Closes bug #28736. Bugfix v0.3.0.
- CI: check broken links in the docs. Closes #28670.
- docs: add scanner and destination requirements.
  Closes bug #28647. Bugfix v0.4.0
- generate: use round_digs variable name in methods.
  Closes bug #28602. Bugfix 1.0.3-dev0
- docs: Change old broken links in the documentation. Closes #28662.
- docs: replace http by https in links. Closes #28661.
- Fix git repository link. Fixes bug #28762. Bugfix v1.0.0.
- docs: add example destination in DEPLOY. Closes #28649.
- docs: Change links to be interpreted by ReST. Closes #28648.
- Force rtfd.io to install the package. Closes bug #28601.
- config: continue when the file is not found. Closes: #28550.
- Stop resolving domains locally and check same flags for the 2nd hop.
  Closes bug #28458, #28471. Bugfix 1.0.4.
- Limit the relays' bandwidth to their consensus bandwidth. Closes #28598.
- globals: add torrc logging options. Closes #28645. Bugfix v0.2.0.
- Limit bandwidth to the relay MaxAdvertisedBandwidth
  Fixes bug #28588. Bugfix 0.8.0.
- Exclude results, then check for the minimum number. Closes bug 28572.
- Make sbws round to 3 significant figures in torflow rounding mode.
  Bugfix on 27337 in sbws 1.0. Part of 28442.

Changed
~~~~~~~~

- tests: remove unused testnets. Fixes bug #29046. Bugfix v0.4.0.
- scanner, destination: Log all possible exceptions.
- docs: Update/improve documentation on how the scanner/generator work.
  Closes: #29149
- Requests: Change make_session to use the TimedSession.
- CI: change to Ubuntu Xenial.
- docs: stop editing changelog on every bug/ticket. Closes ticket #28572.
- Change sbws scaling method to torflow. Closes: #28446.
- Round bandwidths to 2 significant digits by default.
  Implements part of proposal 276. Implements 28451.

Added
~~~~~~

- Send scanner metadata as part of every HTTP request. Closes: #28741
- scanner: log backtrace when not progressing. Closes: 28932

v1.0.2 (2018-11-10)
-------------------

Fixed
~~~~~

-  Update bandwidth file specification version in the ``generator``
   (#28366).
-  Use 5 "=" characters as terminator in the bandwidth files (#28379)

Changed
~~~~~~~

-  Include the headers about eligible relays in all the bandwidth files,
   not only in the ones that does not have enough eligible relays
   (#28365).

v1.0.1 (2018-11-01)
-------------------

Changed
~~~~~~~

-  Change default directories when sbws is run from a system service
   (#28268).

v1.0.0 (2018-10-29)
-------------------

**Important changes**:

-  ``generate`` includes extra statistics header lines when the number
   of eligible relays to include is less than the 60% of the network. It
   does not include the relays' lines.
-  Speed up ``scanner`` by disabling RTT measurements and waiting for
   measurement threads before prioritizing again the list of relays to
   measure.

Fixed
~~~~~

-  Update python minimal version in setup (#28043)
-  Catch unhandled exception when we fail to resolve a domain name
   (#28141)
-  Bandwidth filtered is the maximum between the bandwidth measurements
   and their mean, not the minimum (#28215)
-  Stop measuring the same relay by two threads(#28061)

Changed
~~~~~~~

-  Move ``examples/`` to ``docs/`` (#28040)
-  Number of results comparison and number of results away from each
   other are incorrect (#28041)
-  Stop removing results that are not away from some other X secs
   (#28103)
-  Use secs-away when provided instead of data\_period (#28105)
-  Disable measuring RTTs (#28159)
-  Rename bandwidth file keyvalues (#28197)

Added
-----

-  Write bw file only when the percentage of measured relays is bigger
   than 60% (#28062)
-  When the percentage of measured relays is less than the 60%, do not
   include the relays in the bandwidth file and instead include some
   statistics in the header (#28076)
-  When the percentage of measured relays is less than the 60% and it
   was more before, warn about it (#28155)
-  When the difference between the total consensus bandwidth and the
   total in the bandwidth lines is larger than 50%, warn (#28216)
-  Add documentation about how the bandwidth measurements are selected
   and scaled before writing them to the Bandwidth File (#27692)

v0.8.0 (2018-10-08)
-------------------

**Important changes**:

-  Implement Torflow scaling/aggregation to be able to substitute
   Torflow with sbws without affecting the bandwidth files results.
-  Change stem dependency to 1.7.0, which removes the need for
   ``dependency_links``
-  Update and cleanup documentation

Added
~~~~~

-  Add system physical requirements section to INSTALL (#26937)
-  Warn when there is not enough disk space (#26937)
-  Implement Torflow scaling (#27108)
-  Create methods to easy graph generation and obtain statistics to
   compare with current torflow results.(#27688)
-  Implement rounding bw in bandwidth files to 2 insignificant
   digits(#27337)
-  Filter results in order to include relays in the bandwidth file
   that:(#27338)
-  have at least two measured bandwidths
-  the measured bandwidths are within 24 hours of each other
-  have at least two descriptor observed bandwidths
-  the descriptor observed bandwidths are within 24 hours of each other

Fixed
~~~~~

-  Broken environment variable in default sbws config. To use envvar
   $FOO, write $$FOO in the config.
-  Stop using directory as argument in integration tests (#27342)
-  Fix typo getting configuration option to allow logging to file
   (#27960)
-  Set int type to new arguments that otherwise would be string (#27918)
-  Stop printing arguments default values, since they are printed by
   default (#27916)
-  Use dash instead of underscore in new cli argument names (#27917)

Changed
~~~~~~~

-  sbws install doc is confusing (#27341)
-  Include system and Python dependencies in ``INSTALL``.
-  Include dependencies for docs and tests in ``INSTALL``.
-  Point to ``DEPLOY`` to run sbws.
-  Remove obsolete sections in ``INSTALL``
-  Simplify ``DEPLOY``, reuse terms in the ``glossary``.
-  Remove obsolete ``sbws init`` from ``DEPLOY``.
-  Point to config documentation.
-  Add, unify and reuse terms in ``glossary``.
-  refactor v3bwfile (#27386): move scaling method inside class
-  use custom ``install_command`` to test installation commands while
   ``dependency_links`` is needed until #26914 is fixed. (#27704)
-  documentation cleanup (#27773)
-  split, merge, simplify, extend, reorganize sections and files
-  generate scales as Torflow by default (#27976)
-  Replace stem ``dependency_links`` by stem 1.7.0 (#27705). This also
   eliminates the need for custom ``install_command`` in tox.

v0.7.0 (2018-08-09)
-------------------

**Important changes**:

-  ``cleanup/stale_days`` is renamed to
   ``cleanup/data_files_compress_after_days``
-  ``cleanup/rotten_days`` is renamed to
   ``cleanup/data_files_delete_after_days``
-  sbws now takes as an argument the path to a config file (which
   contains ``sbws_home``) instead of ``sbws_home`` (which contains the
   path to a config file)

Added
~~~~~

-  Log line on start up with sbws version, platform info, and library
   versions (trac#26751)
-  Manual pages (#26926)

Fixed
~~~~~

-  Stop deleting the latest.v3bw symlink. Instead, do an atomic rename.
   (#26740)
-  State file for storing the last time ``sbws scanner`` was started,
   and able to be used for storing many other types of state in the
   future. (GH#166)
-  Log files weren't rotating. Now they are. (#26881)

Changed
~~~~~~~

-  Remove test data v3bw file and generate it from the same test.
   (#26736)
-  Stop using food terms for cleanup-related config options
-  cleanup command now cleans up old v3bw files too (#26701)
-  Make sbws more compatible with system packages: (#26862)
-  Allow a configuration file argument
-  Remove directory argument
-  Create minimal user configuration when running
-  Do not require to run a command to initialize
-  Initialize directories when running
-  Do not require configuration file inside directories specified by the
   configuration

v0.6.0 (2018-07-11)
-------------------

**Important changes**:

-  The way users configure logging has changed. No longer are most users
   expected to be familiar with how to configure python's standard
   logging library with a config file. Instead we've abstracted out the
   setting of log level, format, and destinations to make these settings
   more accessible to users. Expert users familiar with `the logging
   config file
   format <https://docs.python.org/3/library/logging.config.html#logging-config-fileformat>`__
   can still make tweaks.

Summary of changes:

-  Make logging configuration easier for the user.
-  Add UML diagrams to documentation. They can be found in
   docs/source/images/ and regenerated with ``make umlsvg`` in docs/.

Added
~~~~~

-  UML diagrams to documentation. In docs/ run ``make umlsvg`` to
   rebuild them. Requires graphviz to be installed.(GHPR#226)
-  Add metadata to setup.py, useful for source/binary distributions.
-  Add possibility to log to system log. (#26683)
-  Add option to cleanup v3bw files. (#26701)

Fixed
~~~~~

-  Measure relays that have both Exit and BadExit as non-exits, which is
   how clients would use them. (GH#217)
-  Could not init sbws because of a catch-22 related to logging
   configuration. Overhaul how logging is configured. (GH#186 GHPR#224)
-  Call write method of V3BWFile class from the object instance.
   (#26671)
-  Stop calculating median on empty list .(#26666)

Changed
~~~~~~~

-  Remove is\_controller\_ok. Instead catch possible controller
   exceptions and log them

Removed
~~~~~~~

-  Two parsing/plotting scripts in scripts/tools/ that can now be found
   at https://github.com/pastly/v3bw-tools

v0.5.0 (2018-06-26)
-------------------

**Important changes**:

-  Result format changed, causing a version bump to 4. Updating sbws to
   0.5.0 will cause it to ignore results with version less than 4.

Summary of changes:

-  Keep previously-generated v3bw files
-  Allow a relay to limit its weight based on
   RelayBandwidthRate/MaxAdvertisedBandwidth
-  1 CPU usage optimization
-  1 memory usage optimization

Added
~~~~~

-  Use a relay's {,Relay}BandwidthRate/MaxAdvertisedBandwidth as an
   upper bound on the measurements we make for it. (GH#155)
-  Ability to only consider results for a given relay valid if they came
   from when that relay is using its most recent known IP address.
   Thanks Juga. (GH#154 GHPR#199)
-  Maintenance script to help us find functions that are (probably) no
   longer being called.
-  Integration test(s) for RelayPrioritizer (GHPR#206)
-  Git/GitHub usage guidelines to CONTRIBUTING document (GH#208
   GHPR#215)

Fixed
~~~~~

-  Make relay priority calculations take only ~5% of the time they used
   to (3s vs 60s) by using sets instead of lists when selecting
   non-Authority relays. (GH#204)
-  Make relay list refreshing take much less time by not allowing worker
   threads to dogpile on the CPU. Before they would all start requesting
   descriptors from Tor at roughly the same time, causing us to overload
   our CPU core and make the process take unnecessarily long. Now we let
   one thread do the work so it can peg the CPU on its own and get the
   refresh done ASAP. (GH#205)
-  Catch a JSON decode exception on malformed results so sbws can
   continue gracefully (GH#210 GHPR#212)

Changed
~~~~~~~

-  Change the path where the Bandwidth List files are generated: now
   they are stored in ``v3bw`` directory, named ``YYmmdd_HHMMSS.v3bw``,
   and previously generated ones are kept. A ``latest.v3bw`` symlink is
   updated. (GH#179 GHPR#190)
-  Code refactoring in the v3bw classes and generation area
-  Replace v3bw-into-xy bash script with python script to handle a more
   complex v3bw file format (GH#182)

v0.4.1 (2018-06-14)
-------------------

Changed
~~~~~~~

-  If the relay to measure is an exit, put it in the exit position and
   choose a non-exit to help. Previously the relay to measure would
   always be the first hop. (GH#181)
-  Try harder to find a relay to help measure the target relay with two
   changes. Essentially: (1) Instead of only picking from relays that
   are 1.25 - 2.00 times faster than it by consensus weight, try (in
   order) to find a relay that is at least 2.00, 1.75, 1.50, 1.25, or
   v1.00 times as fast. If that fails, instead of giving up, (2) pick the
   fastest relay in the network instead of giving up. This compliments
   the previous change about measuring target exits in the exit
   position.

Fixed
~~~~~

-  Exception that causes sbws to fall back to one measurement thread. We
   first tried fixing something in this area with ``88fae60bc`` but
   neglected to remember that ``.join()`` wants only string arguments
   and can't handle a ``None``. So fix that.
-  Exception when failing to get a relay's ``ed25519_master_key`` from
   Tor and trying to do ``.rstrip()`` on a None.
-  ``earliest_bandwidth`` being the newest bw not the oldest (thanks
   juga0)
-  ``node_id`` was missing the character "$" at the beginning
