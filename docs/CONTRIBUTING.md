# Contributing to Unmanic

The following is a set of guidelines for contributing to the project,
definitely not rules. Use your best judgment, and feel free to suggest changes.

#### Table Of Contents

[How Can I Contribute?](#how-can-i-contribute)
  * [Reporting Bugs](#reporting-bugs)
  * [Suggesting New Features](#suggesting-new-features)
  * [Opening Pull Requests](#opening-pull-requests)

## How Can I Contribute?

### Reporting Bugs

When you are creating a bug report, please include as many details as
possible. Have a look at the [issue template](ISSUE_TEMPLATE.md) for ideas.

> **Note:** If you find a **Closed** issue that seems like it is the same thing
> that you're experiencing, open a new issue and include a link to the original
> issue in the body of your new one.


### Suggesting New Features

You are welcome to submit ideas for new features and enhancements, just include
as many details as possible, including potential implementation options.


### Developing

See [Development Environment Guide](./DEVELOPING.md) for details on setting up a local 
development environment.


### Opening Pull Requests

Code contributions are very welcome. However, please understand that by opening a pull 
requests you hand over copyright ownership of that work to the Unmanic project and the
project owner.
Your contribution becomes licensed under the same license as the project and ownership
is handed over to the project owner. 
This extends upon paragraph 11 of the Terms & Conditions stipulated in the GPL v3.0

All pull requests must be opened to merge into the staging branch. No pull requests 
will be merged into the master branch.

All new python file contributions must contain the following header:

```
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.{{FILE_NAME}}
 
    Written by:               {{YOUR_NAME}} <{{YOUR_EMAIL}}>
    Date:                     {{DAY_NAME}} {{MONTH}} {{DAY_NUMBER}} {{YEAR}}, ({{TIME}} {{AM_PM}})
 
    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved
 
           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:
  
           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.
  
           THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
```

By adding this header you agree to relinquish copyright control to the Unmanic project
and its owner.

Only submissions that conform to this will be merged into the mainline project. This ensures
that Unmanic as a project is free to grow following any path that opens up at the discretion
of the project's owner.

