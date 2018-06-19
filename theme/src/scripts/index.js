'use strict'

if (module.hot) {
  module.hot.accept()
}

import 'babel-polyfill'

import "expose-loader?charts!./charts.js"
import "./charts.js"
import "./closest-polyfill.js"

import { Tooltip, OverflowMenu } from 'carbon-components'
Tooltip.init(document.body);
OverflowMenu.init(document.body);
