"""Default browser action handlers using CDP."""

import asyncio
import platform
from typing import Any

from browser_use.browser.events import (
	ClickElementEvent,
	GoBackEvent,
	GoForwardEvent,
	RefreshEvent,
	ScrollEvent,
	ScrollToTextEvent,
	SendKeysEvent,
	TypeTextEvent,
	UploadFileEvent,
	WaitEvent,
)
from browser_use.browser.views import BrowserError, URLNotAllowedError
from browser_use.browser.watchdog_base import BaseWatchdog
from browser_use.dom.service import EnhancedDOMTreeNode

# Import EnhancedDOMTreeNode and rebuild event models that have forward references to it
# This must be done after all imports are complete
ClickElementEvent.model_rebuild()
TypeTextEvent.model_rebuild()
ScrollEvent.model_rebuild()
UploadFileEvent.model_rebuild()


class DefaultActionWatchdog(BaseWatchdog):
	"""Handles default browser actions like click, type, and scroll using CDP."""

	async def on_ClickElementEvent(self, event: ClickElementEvent) -> None:
		"""Handle click request with CDP."""
		try:
			# Check if session is alive before attempting any operations
			if not self.browser_session.agent_focus or not self.browser_session.agent_focus.target_id:
				error_msg = 'Cannot execute click: browser session is corrupted (target_id=None). Session may have crashed.'
				self.logger.error(f'⚠️ {error_msg}')
				raise BrowserError(error_msg)

			# Use the provided node
			element_node = event.node
			index_for_logging = element_node.element_index or 'unknown'

			# Track initial number of tabs to detect new tab opening
			initial_target_ids = await self.browser_session._cdp_get_all_pages()

			# Check if element is a file input (should not be clicked)
			if self.browser_session.is_file_input(element_node):
				msg = f'Index {index_for_logging} - has an element which opens file upload dialog. To upload files please use a specific function to upload files'
				self.logger.info(msg)
				raise BrowserError(
					'Click triggered a file input element which could not be handled, use the dedicated file upload function instead'
				)

			# Perform the actual click using internal implementation
			await self._click_element_node_impl(element_node, new_tab=event.new_tab)
			download_path = None  # moved to downloads_watchdog.py

			# Build success message
			if download_path:
				msg = f'Downloaded file to {download_path}'
				self.logger.info(f'💾 {msg}')
			else:
				msg = f'Clicked button with index {index_for_logging}: {element_node.get_all_children_text(max_depth=2)}'
				self.logger.info(f'🖱️ {msg}')
			self.logger.debug(f'Element xpath: {element_node.xpath}')

			# Wait a bit for potential new tab to be created
			# This is necessary because tab creation is async and might not be immediate
			await asyncio.sleep(0.5)

			# Clear cached state after click action since DOM might have changed
			self.logger.debug('🔄 Click action completed, clearing cached browser state')
			self.browser_session._cached_browser_state_summary = None
			self.browser_session._cached_selector_map.clear()
			if self.browser_session._dom_watchdog:
				self.browser_session._dom_watchdog.clear_cache()

			# Check if a new tab was opened
			after_target_ids = await self.browser_session._cdp_get_all_pages()
			if len(after_target_ids) > len(initial_target_ids):
				new_tab_msg = 'New tab opened - switching to it'
				msg += f' - {new_tab_msg}'
				self.logger.info(f'🔗 {new_tab_msg}')

				# Optional:Switch to the newly created tab
				# Not recommended usually in order to match normal behavior with Cmd/Ctrl+Click
				# If agent wanted to focus on the new page they would've clicked without new_tab
				# from browser_use.browser.events import SwitchTabEvent

				# last_tab_index = len(after_target_ids) - 1
				# switch_event = self.event_bus.dispatch(SwitchTabEvent(tab_index=last_tab_index))
				# await switch_event

			# Successfully clicked, return None
			return None
		except Exception as e:
			raise

	async def on_TypeTextEvent(self, event: TypeTextEvent) -> None:
		"""Handle text input request with CDP."""
		try:
			# Use the provided node
			element_node = event.node
			index_for_logging = element_node.element_index or 'unknown'

			# Check if this is index 0 or a falsy index - type to the page (whatever has focus)
			if not element_node.element_index or element_node.element_index == 0:
				# Type to the page without focusing any specific element
				await self._type_to_page(event.text)
				self.logger.info(f'⌨️ Typed "{event.text}" to the page (current focus)')
			else:
				try:
					# Try to type to the specific element
					await self._input_text_element_node_impl(element_node, event.text, event.clear_existing)
					self.logger.info(f'⌨️ Typed "{event.text}" into element with index {index_for_logging}')
					self.logger.debug(f'Element xpath: {element_node.xpath}')
				except Exception as e:
					# Element not found or error - fall back to typing to the page
					self.logger.warning(f'Failed to type to element {index_for_logging}: {e}. Falling back to page typing.')
					await self._type_to_page(event.text)
					self.logger.info(f'⌨️ Typed "{event.text}" to the page as fallback')

			# Clear cached state after type action since DOM might have changed
			self.logger.debug('🔄 Type action completed, clearing cached browser state')
			self.browser_session._cached_browser_state_summary = None
			self.browser_session._cached_selector_map.clear()
			if self.browser_session._dom_watchdog:
				self.browser_session._dom_watchdog.clear_cache()

			return None
		except Exception as e:
			raise

	async def on_ScrollEvent(self, event: ScrollEvent) -> None:
		"""Handle scroll request with CDP."""
		# Check if we have a current target for scrolling
		if not self.browser_session.agent_focus:
			error_msg = 'No active target for scrolling'
			raise BrowserError(error_msg)

		try:
			# Convert direction and amount to pixels
			# Positive pixels = scroll down, negative = scroll up
			pixels = event.amount if event.direction == 'down' else -event.amount

			# CRITICAL: CDP calls time out without this, even if the target is already active
			await self.browser_session.agent_focus.cdp_client.send.Target.activateTarget(
				params={'targetId': self.browser_session.agent_focus.target_id}
			)

			# Element-specific scrolling if node is provided
			if event.node is not None:
				element_node = event.node
				index_for_logging = element_node.backend_node_id or 'unknown'

				# Try to scroll the element's container
				success = await self._scroll_element_container(element_node, pixels)
				if success:
					self.logger.info(
						f'📜 Scrolled element {index_for_logging} container {event.direction} by {event.amount} pixels'
					)
					return None

			# Perform target-level scroll
			await self._scroll_with_cdp_gesture(pixels)

			# CRITICAL: CDP calls time out without this, even if the target is already active
			await self.browser_session.agent_focus.cdp_client.send.Target.activateTarget(
				params={'targetId': self.browser_session.agent_focus.target_id}
			)

			# Log success
			self.logger.info(f'📜 Scrolled {event.direction} by {event.amount} pixels')
			return None
		except Exception as e:
			raise

	# ========== Implementation Methods ==========

	async def _click_element_node_impl(self, element_node, new_tab: bool = False) -> str | None:
		"""
		Click an element using pure CDP with multiple fallback methods for getting element geometry.

		Args:
			element_node: The DOM element to click
			new_tab: If True, open any resulting navigation in a new tab
		"""

		try:
			# Check if element is a file input or select dropdown - these should not be clicked
			tag_name = element_node.tag_name.lower() if element_node.tag_name else ''
			element_type = element_node.attributes.get('type', '').lower() if element_node.attributes else ''

			if tag_name == 'select':
				raise Exception('Cannot click on <select> elements. Use select_dropdown_option action instead.')

			if tag_name == 'input' and element_type == 'file':
				raise Exception('Cannot click on file input elements. File uploads must be handled programmatically.')

			# Get CDP client
			cdp_session = await self.browser_session.get_or_create_cdp_session()

			# Get the correct session ID for the element's frame
			# session_id = await self._get_session_id_for_element(element_node)
			session_id = cdp_session.session_id

			# Get element bounds
			backend_node_id = element_node.backend_node_id

			# Get viewport dimensions for visibility checks
			layout_metrics = await cdp_session.cdp_client.send.Page.getLayoutMetrics(session_id=session_id)
			viewport_width = layout_metrics['layoutViewport']['clientWidth']
			viewport_height = layout_metrics['layoutViewport']['clientHeight']

			# Try multiple methods to get element geometry
			quads = []

			# Method 1: Try DOM.getContentQuads first (best for inline elements and complex layouts)
			try:
				content_quads_result = await cdp_session.cdp_client.send.DOM.getContentQuads(
					params={'backendNodeId': backend_node_id}, session_id=session_id
				)
				if 'quads' in content_quads_result and content_quads_result['quads']:
					quads = content_quads_result['quads']
					self.logger.debug(f'Got {len(quads)} quads from DOM.getContentQuads')
			except Exception as e:
				self.logger.debug(f'DOM.getContentQuads failed: {e}')

			# Method 2: Fall back to DOM.getBoxModel
			if not quads:
				try:
					box_model = await cdp_session.cdp_client.send.DOM.getBoxModel(
						params={'backendNodeId': backend_node_id}, session_id=session_id
					)
					if 'model' in box_model and 'content' in box_model['model']:
						content_quad = box_model['model']['content']
						if len(content_quad) >= 8:
							# Convert box model format to quad format
							quads = [
								[
									content_quad[0],
									content_quad[1],  # x1, y1
									content_quad[2],
									content_quad[3],  # x2, y2
									content_quad[4],
									content_quad[5],  # x3, y3
									content_quad[6],
									content_quad[7],  # x4, y4
								]
							]
							self.logger.debug('Got quad from DOM.getBoxModel')
				except Exception as e:
					self.logger.debug(f'DOM.getBoxModel failed: {e}')

			# Method 3: Fall back to JavaScript getBoundingClientRect
			if not quads:
				try:
					result = await cdp_session.cdp_client.send.DOM.resolveNode(
						params={'backendNodeId': backend_node_id},
						session_id=session_id,
					)
					if 'object' in result and 'objectId' in result['object']:
						object_id = result['object']['objectId']

						# Get bounding rect via JavaScript
						bounds_result = await cdp_session.cdp_client.send.Runtime.callFunctionOn(
							params={
								'functionDeclaration': """
									function() {
										const rect = this.getBoundingClientRect();
										return {
											x: rect.left,
											y: rect.top,
											width: rect.width,
											height: rect.height
										};
									}
								""",
								'objectId': object_id,
								'returnByValue': True,
							},
							session_id=session_id,
						)

						if 'result' in bounds_result and 'value' in bounds_result['result']:
							rect = bounds_result['result']['value']
							# Convert rect to quad format
							x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
							quads = [
								[
									x,
									y,  # top-left
									x + w,
									y,  # top-right
									x + w,
									y + h,  # bottom-right
									x,
									y + h,  # bottom-left
								]
							]
							self.logger.debug('Got quad from getBoundingClientRect')
				except Exception as e:
					self.logger.debug(f'JavaScript getBoundingClientRect failed: {e}')

			# If we still don't have quads, fall back to JS click
			if not quads:
				self.logger.warning('⚠️ Could not get element geometry from any method, falling back to JavaScript click')
				try:
					result = await cdp_session.cdp_client.send.DOM.resolveNode(
						params={'backendNodeId': backend_node_id},
						session_id=session_id,
					)
					assert 'object' in result and 'objectId' in result['object'], (
						'Failed to find DOM element based on backendNodeId, maybe page content changed?'
					)
					object_id = result['object']['objectId']

					await cdp_session.cdp_client.send.Runtime.callFunctionOn(
						params={
							'functionDeclaration': 'function() { this.click(); }',
							'objectId': object_id,
						},
						session_id=session_id,
					)
					await asyncio.sleep(0.5)
					# Navigation is handled by BrowserSession via events
					return None
				except Exception as js_e:
					self.logger.error(f'CDP JavaScript click also failed: {js_e}')
					raise Exception(f'Failed to click element: {js_e}')

			# Find the largest visible quad within the viewport
			best_quad = None
			best_area = 0

			for quad in quads:
				if len(quad) < 8:
					continue

				# Calculate quad bounds
				xs = [quad[i] for i in range(0, 8, 2)]
				ys = [quad[i] for i in range(1, 8, 2)]
				min_x, max_x = min(xs), max(xs)
				min_y, max_y = min(ys), max(ys)

				# Check if quad intersects with viewport
				if max_x < 0 or max_y < 0 or min_x > viewport_width or min_y > viewport_height:
					continue  # Quad is completely outside viewport

				# Calculate visible area (intersection with viewport)
				visible_min_x = max(0, min_x)
				visible_max_x = min(viewport_width, max_x)
				visible_min_y = max(0, min_y)
				visible_max_y = min(viewport_height, max_y)

				visible_width = visible_max_x - visible_min_x
				visible_height = visible_max_y - visible_min_y
				visible_area = visible_width * visible_height

				if visible_area > best_area:
					best_area = visible_area
					best_quad = quad

			if not best_quad:
				# No visible quad found, use the first quad anyway
				best_quad = quads[0]
				self.logger.warning('No visible quad found, using first quad')

			# Calculate center point of the best quad
			center_x = sum(best_quad[i] for i in range(0, 8, 2)) / 4
			center_y = sum(best_quad[i] for i in range(1, 8, 2)) / 4

			# Ensure click point is within viewport bounds
			center_x = max(0, min(viewport_width - 1, center_x))
			center_y = max(0, min(viewport_height - 1, center_y))

			# Scroll element into view
			try:
				await cdp_session.cdp_client.send.DOM.scrollIntoViewIfNeeded(
					params={'backendNodeId': backend_node_id}, session_id=session_id
				)
				await asyncio.sleep(0.1)  # Wait for scroll to complete
			except Exception as e:
				self.logger.debug(f'Failed to scroll element into view: {e}')

			# Perform the click using CDP
			# TODO: do occlusion detection first, if element is not on the top, fire JS-based
			# click event instead using xpath of x,y coordinate clicking, because we wont be able to click *through* occluding elements using x,y clicks
			try:
				self.logger.debug(f'👆 Dragging mouse over element before clicking x: {center_x}px y: {center_y}px ...')
				# Move mouse to element
				await cdp_session.cdp_client.send.Input.dispatchMouseEvent(
					params={
						'type': 'mouseMoved',
						'x': center_x,
						'y': center_y,
					},
					session_id=session_id,
				)
				await asyncio.sleep(0.123)

				# Calculate modifier bitmask for CDP
				# CDP Modifier bits: Alt=1, Control=2, Meta/Command=4, Shift=8
				modifiers = 0
				if new_tab:
					# Use platform-appropriate modifier for "open in new tab"
					if platform.system() == 'Darwin':
						modifiers = 4  # Meta/Cmd key
						self.logger.debug('⌘ Using Cmd modifier for new tab click...')
					else:
						modifiers = 2  # Control key
						self.logger.debug('⌃ Using Ctrl modifier for new tab click...')

				# Mouse down
				self.logger.debug(f'👆🏾 Clicking x: {center_x}px y: {center_y}px with modifiers: {modifiers} ...')
				try:
					await asyncio.wait_for(
						cdp_session.cdp_client.send.Input.dispatchMouseEvent(
							params={
								'type': 'mousePressed',
								'x': center_x,
								'y': center_y,
								'button': 'left',
								'clickCount': 1,
								'modifiers': modifiers,
							},
							session_id=session_id,
						),
						timeout=1.0,  # 1 second timeout for mousePressed
					)
					await asyncio.sleep(0.145)
				except TimeoutError:
					self.logger.debug('⏱️ Mouse down timed out (likely due to dialog), continuing...')
					# Don't sleep if we timed out

				# Mouse up
				try:
					await asyncio.wait_for(
						cdp_session.cdp_client.send.Input.dispatchMouseEvent(
							params={
								'type': 'mouseReleased',
								'x': center_x,
								'y': center_y,
								'button': 'left',
								'clickCount': 1,
								'modifiers': modifiers,
							},
							session_id=session_id,
						),
						timeout=1.0,  # 1 second timeout for mouseReleased
					)
				except TimeoutError:
					self.logger.debug('⏱️ Mouse up timed out (likely due to dialog), continuing...')

				self.logger.debug('🖱️ Clicked successfully using x,y coordinates')

			except Exception as e:
				self.logger.warning(f'CDP click failed: {type(e).__name__}: {e}')
				# Fall back to JavaScript click via CDP
				try:
					result = await cdp_session.cdp_client.send.DOM.resolveNode(
						params={'backendNodeId': backend_node_id},
						session_id=session_id,
					)
					assert 'object' in result and 'objectId' in result['object'], (
						'Failed to find DOM element based on backendNodeId, maybe page content changed?'
					)
					object_id = result['object']['objectId']

					await cdp_session.cdp_client.send.Runtime.callFunctionOn(
						params={
							'functionDeclaration': 'function() { this.click(); }',
							'objectId': object_id,
						},
						session_id=session_id,
					)
					await asyncio.sleep(0.5)
					# Navigation is handled by BrowserSession via events
					return None
				except Exception as js_e:
					self.logger.error(f'CDP JavaScript click also failed: {js_e}')
					raise Exception(f'Failed to click element: {e}')

		except URLNotAllowedError as e:
			raise e
		except Exception as e:
			raise Exception(f'Failed to click element: {repr(element_node)}. Error: {str(e)}')

	async def _type_to_page(self, text: str):
		"""
		Type text to the page (whatever element currently has focus).
		This is used when index is 0 or when an element can't be found.
		"""
		try:
			# Get CDP client and session
			cdp_session = await self.browser_session.get_or_create_cdp_session(target_id=None, focus=True)
			await cdp_session.cdp_client.send.Target.activateTarget(params={'targetId': cdp_session.target_id})

			# Type the text character by character to the focused element
			for char in text:
				# Send keydown
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'keyDown',
						'key': char,
					},
					session_id=cdp_session.session_id,
				)
				# Send char for actual text input
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'char',
						'text': char,
					},
					session_id=cdp_session.session_id,
				)
				# Send keyup
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'keyUp',
						'key': char,
					},
					session_id=cdp_session.session_id,
				)
				# Add 18ms delay between keystrokes
				await asyncio.sleep(0.018)

		except Exception as e:
			raise Exception(f'Failed to type to page: {str(e)}')

	async def _check_element_focusability(self, element_node, object_id: str, session_id: str) -> dict[str, Any]:
		"""
		Check if an element is likely to be focusable and visible.

		Returns:
			Dict with keys: 'visible', 'focusable', 'interactive', 'disabled'
		"""
		try:
			cdp_client = self.browser_session.cdp_client

			# Run comprehensive element checks via JavaScript
			check_result = await cdp_client.send.Runtime.callFunctionOn(
				params={
					'functionDeclaration': """
						function() {
							const element = this;
							const computedStyle = window.getComputedStyle(element);
							const rect = element.getBoundingClientRect();
							
							// Check basic visibility
							const isVisible = rect.width > 0 && rect.height > 0 && 
								computedStyle.visibility !== 'hidden' && 
								computedStyle.display !== 'none' &&
								computedStyle.opacity !== '0';
								
							// Check if element is disabled
							const isDisabled = element.disabled || element.hasAttribute('disabled') ||
								element.getAttribute('aria-disabled') === 'true';
								
							// Check if element is focusable by tag and attributes
							const focusableTags = ['input', 'textarea', 'select', 'button', 'a'];
							const hasFocusableTag = focusableTags.includes(element.tagName.toLowerCase());
							const hasTabIndex = element.hasAttribute('tabindex') && element.tabIndex >= 0;
							const isContentEditable = element.contentEditable === 'true';
							
							const isFocusable = !isDisabled && (hasFocusableTag || hasTabIndex || isContentEditable);
							
							// Check if element is interactive (clickable/editable)
							const isInteractive = isFocusable || element.onclick !== null || 
								element.getAttribute('role') === 'button' ||
								element.classList.contains('clickable');
								
							return {
								visible: isVisible,
								focusable: isFocusable,
								interactive: isInteractive,
								disabled: isDisabled,
								bounds: {
									x: rect.left,
									y: rect.top,
									width: rect.width,
									height: rect.height
								},
								tagName: element.tagName.toLowerCase(),
								type: element.type || null
							};
						}
					""",
					'objectId': object_id,
					'returnByValue': True,
				},
				session_id=session_id,
			)

			if 'result' in check_result and 'value' in check_result['result']:
				return check_result['result']['value']
			else:
				self.logger.debug('Element focusability check returned no results')
				return {'visible': False, 'focusable': False, 'interactive': False, 'disabled': True}
		except Exception as e:
			self.logger.debug(f'Element focusability check failed: {e}')
			return {'visible': False, 'focusable': False, 'interactive': False, 'disabled': True}

	async def _input_text_element_node_impl(self, element_node, text: str, clear_existing: bool = True):
		"""
		Input text into an element using pure CDP with improved focus fallbacks.
		"""

		try:
			# Get CDP client
			cdp_client = self.browser_session.cdp_client

			# Get the correct session ID for the element's iframe
			# session_id = await self._get_session_id_for_element(element_node)

			cdp_session = await self.browser_session.get_or_create_cdp_session(target_id=element_node.target_id, focus=True)

			# Get element info
			backend_node_id = element_node.backend_node_id

			# Scroll element into view
			try:
				await cdp_session.cdp_client.send.Target.activateTarget(params={'targetId': element_node.target_id})
				await cdp_session.cdp_client.send.DOM.scrollIntoViewIfNeeded(
					params={'backendNodeId': backend_node_id}, session_id=cdp_session.session_id
				)
				await asyncio.sleep(0.1)
			except Exception as e:
				self.logger.warning(
					f'⚠️ Failed to focus the page {cdp_session} and scroll element {element_node} into view before typing in text: {type(e).__name__}: {e}'
				)

			# Get object ID for the element
			result = await cdp_client.send.DOM.resolveNode(
				params={'backendNodeId': backend_node_id},
				session_id=cdp_session.session_id,
			)
			assert 'object' in result and 'objectId' in result['object'], (
				'Failed to find DOM element based on backendNodeId, maybe page content changed?'
			)
			object_id = result['object']['objectId']

			# Check element focusability before attempting focus
			element_info = await self._check_element_focusability(element_node, object_id, cdp_session.session_id)
			self.logger.debug(f'Element focusability check: {element_info}')

			# Provide helpful warnings for common issues
			if not element_info.get('visible', False):
				self.logger.warning('⚠️ Target element appears to be invisible or has zero dimensions')
			if element_info.get('disabled', False):
				self.logger.warning('⚠️ Target element appears to be disabled')
			if not element_info.get('focusable', False):
				self.logger.warning('⚠️ Target element may not be focusable by standard criteria')

			# Clear existing text if requested
			if clear_existing:
				await cdp_session.cdp_client.send.Runtime.callFunctionOn(
					params={
						'functionDeclaration': 'function() { if (this.value !== undefined) this.value = ""; if (this.textContent !== undefined) this.textContent = ""; }',
						'objectId': object_id,
					},
					session_id=cdp_session.session_id,
				)

			# Try multiple focus strategies
			focused_successfully = False

			# Strategy 1: Try CDP DOM.focus (original method)
			try:
				await cdp_session.cdp_client.send.DOM.focus(
					params={'backendNodeId': backend_node_id},
					session_id=cdp_session.session_id,
				)
				focused_successfully = True
				self.logger.debug('✅ Element focused using CDP DOM.focus')
			except Exception as e:
				self.logger.debug(f'CDP DOM.focus failed: {e}')

				# Strategy 2: Try JavaScript focus as fallback
				try:
					await cdp_session.cdp_client.send.Runtime.callFunctionOn(
						params={
							'functionDeclaration': 'function() { this.focus(); }',
							'objectId': object_id,
						},
						session_id=cdp_session.session_id,
					)
					focused_successfully = True
					self.logger.debug('✅ Element focused using JavaScript focus()')
				except Exception as js_e:
					self.logger.debug(f'JavaScript focus failed: {js_e}')

					# Strategy 3: Try click-to-focus for stubborn elements
					try:
						await cdp_session.cdp_client.send.Runtime.callFunctionOn(
							params={
								'functionDeclaration': 'function() { this.click(); this.focus(); }',
								'objectId': object_id,
							},
							session_id=cdp_session.session_id,
						)
						focused_successfully = True
						self.logger.debug('✅ Element focused using click + focus combination')
					except Exception as click_e:
						self.logger.debug(f'Click + focus failed: {click_e}')

						# Strategy 4: Try simulated mouse click for maximum compatibility
						try:
							# Use bounds from focusability check if available
							bounds = element_info.get('bounds', {})
							if bounds.get('width', 0) > 0 and bounds.get('height', 0) > 0:
								click_x = bounds['x'] + bounds['width'] / 2
								click_y = bounds['y'] + bounds['height'] / 2

								await cdp_session.cdp_client.send.Input.dispatchMouseEvent(
									params={
										'type': 'mousePressed',
										'x': click_x,
										'y': click_y,
										'button': 'left',
										'clickCount': 1,
									},
									session_id=cdp_session.session_id,
								)
								await cdp_session.cdp_client.send.Input.dispatchMouseEvent(
									params={
										'type': 'mouseReleased',
										'x': click_x,
										'y': click_y,
										'button': 'left',
										'clickCount': 1,
									},
									session_id=cdp_session.session_id,
								)
								focused_successfully = True
								self.logger.debug('✅ Element focused using simulated mouse click')
							else:
								self.logger.debug('Element bounds not available for mouse click')
						except Exception as mouse_e:
							self.logger.debug(f'Simulated mouse click failed: {mouse_e}')

			# Log focus result
			if not focused_successfully:
				self.logger.warning('⚠️ All focus strategies failed, typing without explicit focus')

			# Type the text character by character
			for char in text:
				# Send keydown (without text to avoid duplication)
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'keyDown',
						'key': char,
					},
					session_id=cdp_session.session_id,
				)
				# Send char (for actual text input)
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'char',
						'text': char,
						'key': char,
					},
					session_id=cdp_session.session_id,
				)
				# Send keyup (without text to avoid duplication)
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'keyUp',
						'key': char,
					},
					session_id=cdp_session.session_id,
				)
				# Small delay between characters
				await asyncio.sleep(0.05)

		except Exception as e:
			self.logger.error(f'Failed to input text via CDP: {type(e).__name__}: {e}')
			raise BrowserError(f'Failed to input text into element: {repr(element_node)}')

	async def _scroll_with_cdp_gesture(self, pixels: int) -> bool:
		"""
		Scroll using CDP Input.dispatchMouseEvent to simulate mouse wheel.

		Args:
			pixels: Number of pixels to scroll (positive = down, negative = up)

		Returns:
			True if successful, False if failed
		"""
		try:
			# Get CDP client and session
			assert self.browser_session.agent_focus is not None, 'CDP session not initialized - browser may not be connected yet'
			cdp_client = self.browser_session.agent_focus.cdp_client
			session_id = self.browser_session.agent_focus.session_id

			# Get viewport dimensions
			layout_metrics = await cdp_client.send.Page.getLayoutMetrics(session_id=session_id)
			viewport_width = layout_metrics['layoutViewport']['clientWidth']
			viewport_height = layout_metrics['layoutViewport']['clientHeight']

			# Calculate center of viewport
			center_x = viewport_width / 2
			center_y = viewport_height / 2

			# For mouse wheel, positive deltaY scrolls down, negative scrolls up
			delta_y = pixels

			# Dispatch mouse wheel event
			await cdp_client.send.Input.dispatchMouseEvent(
				params={
					'type': 'mouseWheel',
					'x': center_x,
					'y': center_y,
					'deltaX': 0,
					'deltaY': delta_y,
				},
				session_id=session_id,
			)

			self.logger.debug(f'📄 Scrolled via CDP mouse wheel: {pixels}px')
			return True

		except Exception as e:
			self.logger.warning(f'❌ Scrolling via CDP failed: {type(e).__name__}: {e}')
			return False

	async def _scroll_element_container(self, element_node, pixels: int) -> bool:
		"""Try to scroll an element's container using CDP."""
		try:
			cdp_session = await self.browser_session.cdp_client_for_node(element_node)

			# Get element bounds to know where to scroll
			backend_node_id = element_node.backend_node_id
			box_model = await cdp_session.cdp_client.send.DOM.getBoxModel(
				params={'backendNodeId': backend_node_id}, session_id=cdp_session.session_id
			)
			content_quad = box_model['model']['content']

			# Calculate center point
			center_x = (content_quad[0] + content_quad[2] + content_quad[4] + content_quad[6]) / 4
			center_y = (content_quad[1] + content_quad[3] + content_quad[5] + content_quad[7]) / 4

			# Dispatch mouse wheel event at element location
			await cdp_session.cdp_client.send.Input.dispatchMouseEvent(
				params={
					'type': 'mouseWheel',
					'x': center_x,
					'y': center_y,
					'deltaX': 0,
					'deltaY': pixels,
				},
				session_id=cdp_session.session_id,
			)

			return True
		except Exception as e:
			self.logger.debug(f'Failed to scroll element container via CDP: {e}')
			return False

	async def _get_session_id_for_element(self, element_node: EnhancedDOMTreeNode) -> str | None:
		"""Get the appropriate CDP session ID for an element based on its frame."""
		if element_node.frame_id:
			# Element is in an iframe, need to get session for that frame
			try:
				# Get all targets
				targets = await self.browser_session.cdp_client.send.Target.getTargets()

				# Find the target for this frame
				for target in targets['targetInfos']:
					if target['type'] == 'iframe' and element_node.frame_id in str(target.get('targetId', '')):
						# Create temporary session for iframe target without switching focus
						target_id = target['targetId']
						temp_session = await self.browser_session.get_or_create_cdp_session(target_id, focus=False)
						return temp_session.session_id

				# If frame not found in targets, use main target session
				self.logger.debug(f'Frame {element_node.frame_id} not found in targets, using main session')
			except Exception as e:
				self.logger.debug(f'Error getting frame session: {e}, using main session')

		# Use main target session
		assert self.browser_session.agent_focus is not None, 'CDP session not initialized - browser may not be connected yet'
		return self.browser_session.agent_focus.session_id

	async def on_GoBackEvent(self, event: GoBackEvent) -> None:
		"""Handle navigate back request with CDP."""
		cdp_session = await self.browser_session.get_or_create_cdp_session()
		try:
			# Get CDP client and session

			# Get navigation history
			history = await cdp_session.cdp_client.send.Page.getNavigationHistory(session_id=cdp_session.session_id)
			current_index = history['currentIndex']
			entries = history['entries']

			# Check if we can go back
			if current_index <= 0:
				self.logger.warning('⚠️ Cannot go back - no previous entry in history')
				return

			# Navigate to the previous entry
			previous_entry_id = entries[current_index - 1]['id']
			await cdp_session.cdp_client.send.Page.navigateToHistoryEntry(
				params={'entryId': previous_entry_id}, session_id=cdp_session.session_id
			)

			# Wait for navigation
			await asyncio.sleep(0.5)
			# Navigation is handled by BrowserSession via events

			self.logger.info(f'🔙 Navigated back to {entries[current_index - 1]["url"]}')
		except Exception as e:
			raise

	async def on_GoForwardEvent(self, event: GoForwardEvent) -> None:
		"""Handle navigate forward request with CDP."""
		cdp_session = await self.browser_session.get_or_create_cdp_session()
		try:
			# Get navigation history
			history = await cdp_session.cdp_client.send.Page.getNavigationHistory(session_id=cdp_session.session_id)
			current_index = history['currentIndex']
			entries = history['entries']

			# Check if we can go forward
			if current_index >= len(entries) - 1:
				self.logger.warning('⚠️ Cannot go forward - no next entry in history')
				return

			# Navigate to the next entry
			next_entry_id = entries[current_index + 1]['id']
			await cdp_session.cdp_client.send.Page.navigateToHistoryEntry(
				params={'entryId': next_entry_id}, session_id=cdp_session.session_id
			)

			# Wait for navigation
			await asyncio.sleep(0.5)
			# Navigation is handled by BrowserSession via events

			self.logger.info(f'🔜 Navigated forward to {entries[current_index + 1]["url"]}')
		except Exception as e:
			raise

	async def on_RefreshEvent(self, event: RefreshEvent) -> None:
		"""Handle target refresh request with CDP."""
		cdp_session = await self.browser_session.get_or_create_cdp_session()
		try:
			# Reload the target
			await cdp_session.cdp_client.send.Page.reload(session_id=cdp_session.session_id)

			# Wait for reload
			await asyncio.sleep(1.0)

			# Clear cached state after refresh since DOM has been reloaded
			self.logger.debug('🔄 Page refreshed, clearing cached browser state')
			self.browser_session._cached_browser_state_summary = None
			self.browser_session._cached_selector_map.clear()
			if self.browser_session._dom_watchdog:
				self.browser_session._dom_watchdog.clear_cache()

			# Navigation is handled by BrowserSession via events

			self.logger.info('🔄 Target refreshed')
		except Exception as e:
			raise

	async def on_WaitEvent(self, event: WaitEvent) -> None:
		"""Handle wait request."""
		try:
			# Cap wait time at maximum
			actual_seconds = min(max(event.seconds, 0), event.max_seconds)
			if actual_seconds != event.seconds:
				self.logger.info(f'🕒 Waiting for {actual_seconds} seconds (capped from {event.seconds}s)')
			else:
				self.logger.info(f'🕒 Waiting for {actual_seconds} seconds')

			await asyncio.sleep(actual_seconds)
		except Exception as e:
			raise

	async def on_SendKeysEvent(self, event: SendKeysEvent) -> None:
		"""Handle send keys request with CDP."""
		cdp_session = await self.browser_session.get_or_create_cdp_session()
		try:
			# Parse key combination
			keys = event.keys.lower()

			# Handle special key combinations
			if '+' in keys:
				# Handle modifier keys
				parts = keys.split('+')
				key = parts[-1]

				# Calculate modifier bits inline
				# CDP Modifier bits: Alt=1, Control=2, Meta/Command=4, Shift=8
				modifiers = 0
				for part in parts[:-1]:
					part_lower = part.lower()
					if part_lower in ['alt', 'option']:
						modifiers |= 1  # Alt
					elif part_lower in ['ctrl', 'control']:
						modifiers |= 2  # Control
					elif part_lower in ['meta', 'cmd', 'command']:
						modifiers |= 4  # Meta/Command
					elif part_lower in ['shift']:
						modifiers |= 8  # Shift

				# Send key with modifiers
				# Use rawKeyDown for non-text keys (like shortcuts)
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'rawKeyDown',
						'key': key.capitalize() if len(key) == 1 else key,
						'modifiers': modifiers,
					},
					session_id=cdp_session.session_id,
				)
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={
						'type': 'keyUp',
						'key': key.capitalize() if len(key) == 1 else key,
						'modifiers': modifiers,
					},
					session_id=cdp_session.session_id,
				)
			else:
				# Single key
				key_map = {
					'enter': 'Enter',
					'return': 'Enter',
					'tab': 'Tab',
					'delete': 'Delete',
					'backspace': 'Backspace',
					'escape': 'Escape',
					'esc': 'Escape',
					'space': ' ',
					'up': 'ArrowUp',
					'down': 'ArrowDown',
					'left': 'ArrowLeft',
					'right': 'ArrowRight',
					'pageup': 'PageUp',
					'pagedown': 'PageDown',
					'home': 'Home',
					'end': 'End',
				}

				key = key_map.get(keys, keys)

				# Use rawKeyDown for special keys (non-text producing keys)
				# Use keyDown only for regular text characters
				key_type = 'rawKeyDown' if keys in key_map else 'keyDown'

				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={'type': key_type, 'key': key},
					session_id=cdp_session.session_id,
				)
				await cdp_session.cdp_client.send.Input.dispatchKeyEvent(
					params={'type': 'keyUp', 'key': key},
					session_id=cdp_session.session_id,
				)

			self.logger.info(f'⌨️ Sent keys: {event.keys}')

			# Clear cached state if Enter key was pressed (might submit form and change DOM)
			if 'enter' in event.keys.lower() or 'return' in event.keys.lower():
				self.logger.debug('🔄 Enter key pressed, clearing cached browser state')
				self.browser_session._cached_browser_state_summary = None
				self.browser_session._cached_selector_map.clear()
				if self.browser_session._dom_watchdog:
					self.browser_session._dom_watchdog.clear_cache()
		except Exception as e:
			raise

	async def on_UploadFileEvent(self, event: UploadFileEvent) -> None:
		"""Handle file upload request with CDP."""
		try:
			# Use the provided node
			element_node = event.node
			index_for_logging = element_node.element_index or 'unknown'

			# Check if it's a file input
			if not self.browser_session.is_file_input(element_node):
				raise Exception(f'Element {index_for_logging} is not a file input')

			# Get CDP client and session
			cdp_client = self.browser_session.cdp_client
			session_id = await self._get_session_id_for_element(element_node)

			# Set file(s) to upload
			backend_node_id = element_node.backend_node_id
			await cdp_client.send.DOM.setFileInputFiles(
				params={
					'files': [event.file_path],
					'backendNodeId': backend_node_id,
				},
				session_id=session_id,
			)

			self.logger.info(f'📎 Uploaded file {event.file_path} to element {index_for_logging}')
		except Exception as e:
			raise

	async def on_ScrollToTextEvent(self, event: ScrollToTextEvent) -> None:
		"""Handle scroll to text request with CDP. Raises exception if text not found."""
		# Get CDP client and session
		cdp_client = self.browser_session.cdp_client
		if self.browser_session.agent_focus is None:
			raise BrowserError('CDP session not initialized - browser may not be connected yet')
		session_id = self.browser_session.agent_focus.session_id

		# Enable DOM
		await cdp_client.send.DOM.enable(session_id=session_id)

		# Get document
		doc = await cdp_client.send.DOM.getDocument(params={'depth': -1}, session_id=session_id)
		root_node_id = doc['root']['nodeId']

		# Search for text using XPath
		search_queries = [
			f'//*[contains(text(), "{event.text}")]',
			f'//*[contains(., "{event.text}")]',
			f'//*[@*[contains(., "{event.text}")]]',
		]

		found = False
		for query in search_queries:
			try:
				# Perform search
				search_result = await cdp_client.send.DOM.performSearch(params={'query': query}, session_id=session_id)
				search_id = search_result['searchId']
				result_count = search_result['resultCount']

				if result_count > 0:
					# Get the first match
					node_ids = await cdp_client.send.DOM.getSearchResults(
						params={'searchId': search_id, 'fromIndex': 0, 'toIndex': 1},
						session_id=session_id,
					)

					if node_ids['nodeIds']:
						node_id = node_ids['nodeIds'][0]

						# Scroll the element into view
						await cdp_client.send.DOM.scrollIntoViewIfNeeded(params={'nodeId': node_id}, session_id=session_id)

						found = True
						self.logger.info(f'📜 Scrolled to text: "{event.text}"')
						break

				# Clean up search
				await cdp_client.send.DOM.discardSearchResults(params={'searchId': search_id}, session_id=session_id)
			except Exception as e:
				self.logger.debug(f'Search query failed: {query}, error: {e}')
				continue

		if not found:
			# Fallback: Try JavaScript search
			js_result = await cdp_client.send.Runtime.evaluate(
				params={
					'expression': f'''
							(() => {{
								const walker = document.createTreeWalker(
									document.body,
									NodeFilter.SHOW_TEXT,
									null,
									false
								);
								let node;
								while (node = walker.nextNode()) {{
									if (node.textContent.includes("{event.text}")) {{
										node.parentElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
										return true;
									}}
								}}
								return false;
							}})()
						'''
				},
				session_id=session_id,
			)

		if js_result.get('result', {}).get('value'):
			self.logger.info(f'📜 Scrolled to text: "{event.text}" (via JS)')
			return None
		else:
			self.logger.warning(f'⚠️ Text not found: "{event.text}"')
			raise BrowserError(f'Text not found: "{event.text}"', details={'text': event.text})

		# If we got here and found is True, return None (success)
		if found:
			return None
		else:
			raise BrowserError(f'Text not found: "{event.text}"', details={'text': event.text})
