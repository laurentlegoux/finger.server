# fingerd — a Finger protocol server for MicroPythonOS  
  
Because your microcontroller deserves to be fingered. On port 79, like it's 1977.  
  
## What is this?  
  
A `boot_completed` service (`FingerBootService`) that listens on TCP port 79  
and answers Finger protocol queries, plus a launcher activity  
(`FingerSettings`) to configure it. Every query executes `finger.py` from  
your finger directory; user queries additionally append the classic user  
files — `plan`, `project`, `pgpkey`, `forward` — whichever exist.  
  
## A brief and entirely accurate history of Finger  
  
- **1971**: Les Earnest at Stanford writes the first `finger` program so  
  people could check who was logged into the lab's PDP-10 — mostly to  
  figure out who to blame when the computer was slow. The name comes from  
  the idea of "pointing a finger" at someone. The 1970s were simpler times.  
- **1977**: Formalized as **RFC 742**. The protocol spec is roughly:  
  "send a name, get some text back." Networking was easy before anyone  
  invented security.  
- **1988**: The Morris Worm exploits a buffer overflow in `fingerd` and  
  takes down a chunk of the early internet. Finger's reputation never  
  fully recovers.  
- **1991**: **RFC 1288** tidies things up and politely suggests that maybe  
  servers shouldn't reveal everyone's home directory and phone number to  
  anonymous strangers. Most of the internet responds by turning fingerd  
  off entirely.  
- **1990s**: John Carmack of id Software turns his `.plan` file into a  
  proto-blog, posting regular updates about Doom and Quake development.  
  For a brief, glorious moment, `finger carmack@idsoftware.com` was the  
  hottest news feed in gaming. This was blogging before blogging, on a  
  protocol older than most of its readers.  
- **2000s+**: Finger dies quietly, buried under privacy policies, firewalls,  
  and the general realization that broadcasting your email forwarding  
  address to the whole internet was maybe not a great idea.  
- **Now**: You are running it on a microcontroller with 500 KB of RAM.  
  Les Earnest would be proud. Or horrified. Probably both.  
  
## Protocol (all of it)  
  
```text  
Client says "user\r\n"  →  finger.py output + plan/project/pgpkey/forward  
Client says "\r\n"      →  finger.py output only (sysinfo, by default)  
Client closes           →  Server closes

That's the whole protocol. No headers. No TLS. No JSON. No mercy.
finger.py — the plan file that thinks

Traditionally, .plan was a static text file you edited by hand, like an
animal. This fingerd instead executes finger.py — a MicroPython script
in your finger directory — on every query, captures whatever it
print()s, and serves that. The script gets a query global containing
the decoded request line ("" for an empty query), so it can branch:

if query:  
    print("You asked about: %s" % query)  
else:  
    print("MicroPythonOS — uptime, RAM, IP, the usual bragging")

This turns a 50-year-old read-only protocol into a tiny RPC endpoint.
Some ideas, none of them advisable:

    Serve live sensor data: temperature, battery, free heap — a status
    page older than HTTP itself.
    A fortune cookie server. finger wisdom@badge at a conference.
    A guestbook: append queries to a file, serve the file back.
    Carmack-style devlog, but generated — rotate through your last N
    commit messages.
    finger coffee@kitchen-esp32 → whether the coffee is ready. This is
    what the protocol was always for, deep down.

The script is re-read and re-executed per connection — edit it, finger
again, done. No reboot. Keep it fast: it runs inside the request handler,
so a while True makes your fingerd a very authentic 1970s hang.
Files served

For a non-empty query, after finger.py output, these files are appended
in order, whichever exist:
File	Traditional meaning
plan	What you're up to. Started as "what I'm doing today" on the PDP-10, became Carmack's proto-blog, died, and is now reborn as the ancestor of the status update, the tweet, and the LinkedIn post nobody asked for.
project	What you're working on — traditionally one line, because in 1977 brevity was enforced by teletype. The original "currently working on" field, 40 years before GitHub profiles.
pgpkey	Your ASCII-armored public key, so fingerers could encrypt mail to you. The 1990s idea of a keyserver. Public. Not private. We cannot stress this enough.
forward	Where your mail actually goes — the .forward file that told sendmail to redirect your email. Broadcasting it to anonymous strangers was, in hindsight, a gift to the spam industry.

Missing files are skipped silently. If nothing produces output at all:
no plan — which is also a fair description of this project.
Settings

Tap the fingerd icon in the launcher:

    Finger server — On/Off (applies at boot)
    Port — default 79 (applies after reboot)
    Finger dir — browse to pick the directory holding finger.py and
    the static files (default: the app directory, so it works out of the box)

Usage

The finger server is scheduled to start 30 seconds after boot. You need to
be patient — a virtue the protocol rewards.

Install a finger client on your other computer (not the microcontroller,
the other one!):

finger user@<device-ip>     # finger.py + your files  
finger @<device-ip>         # finger.py only (sysinfo)

Or in bash, if you don't have finger installed:

echo user | nc <device-ip> 79

If you wonder whether you're the last person using this advanced
technology:

finger ring@thebackupbox.net

Security note

This is a faithful reproduction of a 1970s protocol, including the 1970s
approach to security: none. It serves whatever finger.py prints and
whatever files sit in the finger directory to anyone who can reach port
79 — and finger.py is code execution, so treat the finger directory
like root's home directory, because it basically is. Do not put your
private PGP key in pgpkey. Do not put your passwords in plan.
Do not finger and drive.
Warning

RFC 1288 compliance is aspirational.
License

MIT