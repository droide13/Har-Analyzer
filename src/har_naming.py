#!/usr/bin/env python3
"""
har_naming.py

Builds a standardized filename for .har files based on the test scenario
that produced them, and prints a friendly summary of what was chosen.

Filename format:
    <domain>-interact-(loa/nav/ema/sig/log)-cookies-(acc/den/ign)-visit-(fir/sec/del)-extra-(3letters)-yy-mm-dd-hh.har

Where:
    interact -> load / navigate / enter email / sign up / login
                -> loa / nav / ema / sig / log
    cookies  -> accept / deny / ignore
                -> acc / den / ign
    visit    -> first visit / second visit (reuse previous cookies or
                anything already there) / delete cookies and reload to
                regenerate everything from scratch
                -> fir / sec / del
                Optional. Defaults to "first" if not given.
    extra    -> first 3 letters of a free-text word, or "000" if not given

Invocation:
    python har_naming.py domain.com load accept
    python har_naming.py domain.com load accept --visit second
    python har_naming.py domain.com login accept --visit delete --extra staging
"""

import argparse
import sys
from datetime import datetime

# Maps from the full human word (what you type on the CLI) to the
# 3-letter code that goes into the filename.
INTERACT_CODES: dict[str, str] = {
    "load": "LOA",
    "navigate": "NAV",
    "enter_email": "EMA",
    "email": "EMA",  # convenience alias
    "sign_up": "SIG",
    "signup": "SIG",  # convenience alias
    "login": "LOG",
}

COOKIES_CODES: dict[str, str] = {
    "accept": "ACC",
    "deny": "DEN",
    "ignore": "IGN",
}

VISIT_CODES: dict[str, str] = {
    "first": "FIR",
    "second": "SEC",
    "delete": "DEL",
}

# visit is optional on the CLI, this is what it defaults to.
DEFAULT_VISIT: str = "first"


def get_har_filename(
    domain: str,
    interact: str,
    cookies: str,
    visit: str = DEFAULT_VISIT,
    extra: str = "",
    now: datetime | None = None,
) -> str:
    """
    Build the .har filename for a given test scenario.

    Args:
        domain: The domain under test, e.g. "domain.com".
        interact: One of "load", "navigate", "enter_email" (or "email"),
                  "sign_up" (or "signup"), "login".
        cookies: One of "accept", "deny", "ignore".
        visit: One of "first", "second", "delete". Optional, defaults to
               "first" (a fresh, first-time visit).
        extra: Optional free-text word. Only its first 3 letters are kept
               (lowercased). If empty, "000" is used instead.
        now: Optional datetime override, mainly useful for testing.
             Defaults to the current local time.

    Returns:
        The fully formatted filename, e.g.:
        "domain.com-interact-loa-cookies-acc-visit-fir-extra-000-26-07-02-14.har"

    Raises:
        ValueError: if interact, cookies, or visit is not a recognized option.
    """
    interact_key = interact.strip().lower()
    cookies_key = cookies.strip().lower()
    visit_key = visit.strip().lower() if visit.strip() else DEFAULT_VISIT

    if interact_key not in INTERACT_CODES:
        valid = ", ".join(sorted(set(INTERACT_CODES)))
        raise ValueError(f"Invalid interact '{interact}'. Valid options: {valid}")

    if cookies_key not in COOKIES_CODES:
        valid = ", ".join(sorted(set(COOKIES_CODES)))
        raise ValueError(f"Invalid cookies '{cookies}'. Valid options: {valid}")

    if visit_key not in VISIT_CODES:
        valid = ", ".join(sorted(set(VISIT_CODES)))
        raise ValueError(f"Invalid visit '{visit}'. Valid options: {valid}")

    interact_code = INTERACT_CODES[interact_key]
    cookies_code = COOKIES_CODES[cookies_key]
    visit_code = VISIT_CODES[visit_key]

    # Extra is free text: just take the first 3 letters, uppercased for
    # consistency with the other codes. If nothing was passed, fall back
    # to the "000" placeholder.
    extra_code = extra.strip().upper()[:3] if extra.strip() else "000"

    timestamp = (now or datetime.now()).strftime("%y-%m-%d-%H")

    return (
        f"{domain}-interact-{interact_code}"
        f"-cookies-{cookies_code}"
        f"-visit-{visit_code}"
        f"-extra-{extra_code}"
        f"-{timestamp}.har"
    )


def pretty_print_summary(
    domain: str,
    interact: str,
    cookies: str,
    visit: str,
    extra: str,
    filename: str,
) -> None:
    """
    Print a human-friendly, nicely formatted summary of the test scenario
    followed by the resulting filename.

    Args:
        domain: The domain under test.
        interact: The raw interact word as passed in (e.g. "load").
        cookies: The raw cookies word as passed in (e.g. "accept").
        visit: The raw visit word as passed in (e.g. "first"). May be empty,
               in which case the default is shown.
        extra: The raw extra word as passed in, may be empty.
        filename: The final generated .har filename.
    """
    visit_display = visit.strip() if visit.strip() else f"{DEFAULT_VISIT} (default)"
    extra_display = extra.strip() if extra.strip() else "none"

    separator = "-" * 40
    print(separator)
    print("HAR TEST SCENARIO")
    print(separator)
    print(f"  test in course : {domain}")
    print(f"  domain         : {domain}")
    print(f"  interact       : {interact}")
    print(f"  cookies        : {cookies}")
    print(f"  visit          : {visit_display}")
    print(f"  extra          : {extra_display}")
    print(separator)
    print("file name")
    print(filename)
    print(separator)


def print_usage_help() -> None:
    """
    Print a friendly, example-driven usage guide.

    Shown when the script is run with no arguments at all, so a first-time
    user immediately understands what to type instead of just getting a
    terse argparse error.
    """
    separator = "-" * 55
    print(separator)
    print("HAR NAMING TOOL - no arguments provided")
    print(separator)
    print("Usage:")
    print("  python har_naming.py <domain> <interact> <cookies> [options]")
    print()
    print("Required arguments:")
    print("  domain    e.g. domain.com")
    print("  interact  one of: load / navigate / enter_email (alias: email)")
    print("                    sign_up (alias: signup) / login")
    print("  cookies   one of: accept / deny / ignore")
    print()
    print("Optional flags:")
    print("  --visit   one of: first / second / delete")
    print("            first  -> a fresh, first-time visit")
    print("            second -> revisit reusing previous cookies/state")
    print("            delete -> wipe cookies and reload to regenerate")
    print("            Defaults to 'first' if not given.")
    print("  --extra   any word, first 3 letters are used. If omitted, ")
    print("            '000' is used in the filename instead.")
    print()
    print("Examples:")
    print("  python har_naming.py domain.com load accept")
    print("  python har_naming.py domain.com navigate deny --visit second")
    print("  python har_naming.py domain.com login accept --visit delete --extra staging")
    print(separator)


def main() -> None:
    """Parse CLI arguments, build the filename, and print the summary."""
    parser = argparse.ArgumentParser(
        description="Generate a standardized .har filename for a test scenario."
    )
    parser.add_argument("domain", help="Domain under test, e.g. domain.com")
    parser.add_argument(
        "interact",
        help="Interaction type: load / navigate / enter_email / sign_up / login",
    )
    parser.add_argument("cookies", help="Cookies handling: accept / deny / ignore")
    parser.add_argument(
        "--visit",
        default=DEFAULT_VISIT,
        help="Visit type: first / second / delete. Defaults to 'first'.",
    )
    parser.add_argument(
        "--extra",
        default="",
        help="Optional free-text word describing the extra context (first "
        "3 letters are used). Defaults to '000' if omitted.",
    )

    # If the user just runs "python har_naming.py" with nothing else,
    # argparse's default error is terse and not very welcoming. Catch
    # that case early and show a proper how-to-use guide instead.
    if len(sys.argv) == 1:
        print_usage_help()
        sys.exit(0)

    args = parser.parse_args()

    try:
        filename = get_har_filename(
            domain=args.domain,
            interact=args.interact,
            cookies=args.cookies,
            visit=args.visit,
            extra=args.extra,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    pretty_print_summary(
        domain=args.domain,
        interact=args.interact,
        cookies=args.cookies,
        visit=args.visit,
        extra=args.extra,
        filename=filename,
    )


if __name__ == "__main__":
    main()