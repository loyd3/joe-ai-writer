<template>
  <div
    class="block-editor"
    :class="{ 'focus-mode': isFocusMode, 'multi-select': isMultiSelectMode, 'preview-mode': previewMode }"
    @click="handleEditorClick"
  >
    <!-- 多选块工具栏 -->
    <Teleport to="body">
      <Transition name="multi-select-toolbar">
        <div v-if="isMultiSelectMode && selectedBlocks.size > 0" class="multi-select-toolbar">
          <span class="selected-count">已选 {{ selectedBlocks.size }} 个块</span>
          <button type="button" class="toolbar-btn" @click="copySelectedBlocks" title="复制 (Ctrl+C)">
            <el-icon><DocumentCopy /></el-icon>
            <span>复制</span>
          </button>
          <button type="button" class="toolbar-btn" @click="cutSelectedBlocks" title="剪切 (Ctrl+X)">
            <el-icon><Scissor /></el-icon>
            <span>剪切</span>
          </button>
          <el-dropdown
            trigger="click"
            class="multi-batch-style-dropdown"
            popper-class="multi-batch-style-popper"
            @command="onMultiBatchStyleCommand"
          >
            <button type="button" class="toolbar-btn toolbar-btn-dropdown" title="批量：文体、整段字体、移动（预览模式下仅可移动）">
              <el-icon><Operation /></el-icon>
              <span>批量样式</span>
              <el-icon class="batch-dd-caret"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu class="multi-batch-style-menu">
                <el-dropdown-item disabled class="batch-menu-section-title" command="__h1">文体</el-dropdown-item>
                <el-dropdown-item command="type:paragraph" :disabled="previewMode">
                  <el-icon><Document /></el-icon> 正文
                </el-dropdown-item>
                <el-dropdown-item command="type:heading" :disabled="previewMode">
                  <el-icon><Top /></el-icon> 大标题
                </el-dropdown-item>
                <el-dropdown-item command="type:subheading" :disabled="previewMode">
                  <el-icon><Rank /></el-icon> 小标题
                </el-dropdown-item>
                <el-dropdown-item command="type:quote" :disabled="previewMode">
                  <el-icon><ChatDotRound /></el-icon> 引用
                </el-dropdown-item>
                <el-dropdown-item command="type:list" :disabled="previewMode">
                  <el-icon><List /></el-icon> 列表
                </el-dropdown-item>
                <el-dropdown-item command="type:code" :disabled="previewMode">
                  <el-icon><Operation /></el-icon> 代码块
                </el-dropdown-item>
                <el-dropdown-item command="type:divider" divided :disabled="previewMode">
                  <el-icon><Minus /></el-icon> 分割线
                </el-dropdown-item>
                <el-dropdown-item disabled class="batch-menu-section-title" command="__h2">整段字体</el-dropdown-item>
                <el-dropdown-item command="fmt:bold" :disabled="previewMode">
                  <span class="fmt-bold">B</span> 全文加粗
                </el-dropdown-item>
                <el-dropdown-item command="fmt:italic" :disabled="previewMode">
                  <span class="fmt-italic">I</span> 全文斜体
                </el-dropdown-item>
                <el-dropdown-item command="fmt:underline" divided :disabled="previewMode">
                  <span class="fmt-underline">U</span> 全文下划线
                </el-dropdown-item>
                <el-dropdown-item disabled class="batch-menu-section-title" command="__h3">移动</el-dropdown-item>
                <el-dropdown-item command="move:up" :disabled="!canMoveUpMultiToolbar">
                  <el-icon><ArrowUp /></el-icon> 整体上移
                </el-dropdown-item>
                <el-dropdown-item command="move:down" :disabled="!canMoveDownMultiToolbar">
                  <el-icon><ArrowDown /></el-icon> 整体下移
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <button
            type="button"
            class="toolbar-btn ai-btn"
            @click="emitPolishSelected"
            title="AI 润色（选中多个块）"
          >
            <el-icon><Brush /></el-icon>
            <span>AI 润色</span>
          </button>
          <button
            type="button"
            class="toolbar-btn ai-btn"
            @click="emitReviseSelected"
            title="AI 修改（选中多个块）"
          >
            <el-icon><EditPen /></el-icon>
            <span>AI 修改</span>
          </button>
          <button
            type="button"
            class="toolbar-btn ai-btn"
            @click="emitExpandSelected"
            title="AI 扩展（选中多个块）"
          >
            <el-icon><MagicStick /></el-icon>
            <span>AI 扩展</span>
          </button>
          <button
            type="button"
            class="toolbar-btn ai-btn"
            @click="emitGenerateImageForSelection"
            title="根据选中段落生成插图（Ctrl+点击多选）"
          >
            <el-icon><Picture /></el-icon>
            <span>选中生成插图</span>
          </button>
          <button
            type="button"
            class="toolbar-btn"
            :disabled="!canMoveUpMultiToolbar"
            @click="tryMoveBlocks(-1, multiToolbarAnchorIndex)"
            title="整体上移 (Ctrl+Shift+↑)"
          >
            <el-icon><ArrowUp /></el-icon>
            <span>上移</span>
          </button>
          <button
            type="button"
            class="toolbar-btn"
            :disabled="!canMoveDownMultiToolbar"
            @click="tryMoveBlocks(1, multiToolbarAnchorIndex)"
            title="整体下移 (Ctrl+Shift+↓)"
          >
            <el-icon><ArrowDown /></el-icon>
            <span>下移</span>
          </button>
          <button type="button" class="toolbar-btn delete" @click="deleteSelectedBlocks" title="删除 (Delete)">
            <el-icon><Delete /></el-icon>
            <span>删除</span>
          </button>
          <button type="button" class="toolbar-btn" @click="clearBlockSelection" title="取消选择 (Esc)">
            <el-icon><Close /></el-icon>
            <span>取消</span>
          </button>
        </div>
      </Transition>
    </Teleport>

    <!-- 斜杠命令菜单 -->
    <Teleport to="body">
      <Transition name="slash-menu">
        <div
          v-if="slashMenuVisible"
          class="slash-menu"
          :style="slashMenuStyle"
        >
          <div class="slash-menu-header">基本块</div>
          <div
            v-for="(cmd, idx) in filteredSlashCommands"
            :key="cmd.id"
            class="slash-menu-item"
            :class="{ active: selectedSlashIndex === idx }"
            @mousedown.prevent
            @click="applySlashCommand(idx, currentSlashBlockIndex)"
          >
            <div class="slash-icon">
              <el-icon v-if="cmd.icon === 'Top'"><Top /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Rank'"><Rank /></el-icon>
              <el-icon v-else-if="cmd.icon === 'ChatDotRound'"><ChatDotRound /></el-icon>
              <el-icon v-else-if="cmd.icon === 'List'"><List /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Operation'"><Operation /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Minus'"><Minus /></el-icon>
              <el-icon v-else-if="cmd.icon === 'Document'"><Document /></el-icon>
            </div>
            <div class="slash-info">
              <span class="slash-label">{{ cmd.label }}</span>
              <span class="slash-shortcut">{{ cmd.shortcut }}</span>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>

    <div
      v-if="!modelValue.length"
      class="empty-state"
      @click="addBlock(-1)"
      @contextmenu.prevent="onEmptyAreaContextMenu($event)"
    >
      <div class="empty-icon">
        <el-icon><EditPen /></el-icon>
      </div>
      <span>点击开始写作，记录您的灵感...</span>
      <span class="shortcut-hint">Ctrl+1~6 切换块 · Ctrl+B/I/U 格式 · Ctrl+Z/Y 撤销 · Ctrl+↑↓ 导航 · Ctrl+Shift+↑↓ 移动块 · / 斜杠命令 · Ctrl+点击多选 · Ctrl+C/X/V 复制剪切粘贴</span>
    </div>

    <div
      v-else
      :ref="bindScrollEl"
      class="block-list-scroll"
      @scroll.passive="onBlockListScroll"
    >
      <div
        v-if="virtualListReady"
        class="virtual-pad virtual-pad-top"
        :style="{ height: virtualTopPad + 'px' }"
        aria-hidden="true"
      />
      <div
        v-for="row in displayedRows"
        :key="row.block.id"
        :ref="el => setBlockWrapperRef(el, row.index)"
        class="block-wrapper"
        :class="{
          'is-focused': focusedIndex === row.index,
          'is-toolbar-visible': toolbarVisibleIndex === row.index,
          'is-selected': selectedBlocks.has(row.index),
          [`type-${row.block.type}`]: true
        }"
        @mouseenter="onBlockMouseEnter(row.index)"
        @mouseleave="onBlockMouseLeave"
        @mousedown="handleBlockMouseDown(row.index, $event)"
      >
      <!-- 快捷操作栏：悬停 3s 或选中内容 3s 后显示 -->
      <Transition name="toolbar">
        <div v-show="toolbarVisibleIndex === row.index" class="quick-toolbar" @mousedown.prevent>
          <button type="button" class="toolbar-btn" :disabled="!canUndo" @click.stop="undo()" title="撤销 (Ctrl+Z)">
            <el-icon><RefreshLeft /></el-icon>
            <span>撤销</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="!canRedo" @click.stop="redo()" title="重做 (Ctrl+Shift+Z)">
            <el-icon><RefreshRight /></el-icon>
            <span>重做</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn" :disabled="previewMode" :class="{ active: row.block.type === 'heading' }" @click.stop="handleCommand('heading', row.index)" title="标题 (Ctrl+1)">
            <el-icon><Top /></el-icon>
            <span>标题</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="previewMode" :class="{ active: row.block.type === 'subheading' }" @click.stop="handleCommand('subheading', row.index)" title="小标题 (Ctrl+2)">
            <el-icon><Rank /></el-icon>
            <span>小标题</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="previewMode" :class="{ active: row.block.type === 'quote' }" @click.stop="handleCommand('quote', row.index)" title="引用 (Ctrl+3)">
            <el-icon><ChatDotRound /></el-icon>
            <span>引用</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="previewMode" :class="{ active: row.block.type === 'list' }" @click.stop="handleCommand('list', row.index)" title="列表 (Ctrl+4)">
            <el-icon><List /></el-icon>
            <span>列表</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="previewMode" :class="{ active: row.block.type === 'code' }" @click.stop="handleCommand('code', row.index)" title="代码块 (Ctrl+5)">
            <el-icon><Operation /></el-icon>
            <span>代码</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="previewMode" :class="{ active: row.block.type === 'divider' }" @click.stop="handleCommand('divider', row.index)" title="分割线 (Ctrl+6)">
            <el-icon><Minus /></el-icon>
            <span>分割线</span>
          </button>
          <button type="button" class="toolbar-btn" :disabled="previewMode" :class="{ active: row.block.type === 'paragraph' }" @click.stop="handleCommand('paragraph', row.index)" title="正文 (Ctrl+0)">
            <el-icon><Document /></el-icon>
            <span>正文</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn ai-btn" @click.stop="emitPolish(row.index)" title="AI 润色">
            <el-icon><Brush /></el-icon>
            <span>AI 润色</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn format-btn" :disabled="previewMode" :class="{ active: isFormatActive(row.index, 'bold') }" @click.stop="applyFormat(row.index, 'bold')" title="加粗 (Ctrl+B)">
            <span class="fmt-bold">B</span>
          </button>
          <button type="button" class="toolbar-btn format-btn" :disabled="previewMode" :class="{ active: isFormatActive(row.index, 'italic') }" @click.stop="applyFormat(row.index, 'italic')" title="斜体 (Ctrl+I)">
            <span class="fmt-italic">I</span>
          </button>
          <button type="button" class="toolbar-btn format-btn" :disabled="previewMode" :class="{ active: isFormatActive(row.index, 'underline') }" @click.stop="applyFormat(row.index, 'underline')" title="下划线 (Ctrl+U)">
            <span class="fmt-underline">U</span>
          </button>
          <span class="toolbar-divider" />
          <button
            type="button"
            class="toolbar-btn"
            :disabled="!canMoveUpForToolbar(row.index)"
            @click.stop="tryMoveBlocks(-1, row.index)"
            title="上移块 (Ctrl+Shift+↑)"
          >
            <el-icon><ArrowUp /></el-icon>
            <span>上移</span>
          </button>
          <button
            type="button"
            class="toolbar-btn"
            :disabled="!canMoveDownForToolbar(row.index)"
            @click.stop="tryMoveBlocks(1, row.index)"
            title="下移块 (Ctrl+Shift+↓)"
          >
            <el-icon><ArrowDown /></el-icon>
            <span>下移</span>
          </button>
          <span class="toolbar-divider" />
          <button type="button" class="toolbar-btn delete" :disabled="modelValue.length <= 1" @click.stop="handleCommand('delete', row.index)" title="删除块 (Ctrl+Shift+D)">
            <el-icon><Delete /></el-icon>
          </button>
        </div>
      </Transition>
      <div class="block-handle" @click.stop="addBlock(row.index)">
        <el-icon><Plus /></el-icon>
      </div>
      
      <template v-if="row.block.type === 'image'">
        <div class="block-image-section">
          <img
            v-if="row.block.props?.src"
            :src="resolveImageUrl(String(row.block.props.src))"
            class="block-image-el"
            alt=""
            draggable="false"
          />
          <div v-else class="block-image-placeholder">暂无图片地址</div>
        </div>
        <div
          :ref="el => setBlockRef(el, row.index)"
          class="block-content block-type-image-caption"
          :data-type="row.block.type"
          :contenteditable="!previewMode"
          @input="updateBlock(row.index)"
          @focus="onBlockFocus(row.index)"
          @blur="handleBlur"
          @contextmenu.prevent="onBlockContextMenu(row.index, $event)"
          @keydown.enter.prevent="handleEnter(row.index, $event)"
          @keydown.backspace="handleBackspace(row.index, $event)"
          @keydown.up="moveFocus(row.index, -1, $event)"
          @keydown.down="moveFocus(row.index, 1, $event)"
          @keydown="handleKeydown(row.index, $event)"
          @keydown.ctrl.a.prevent="handleSelectAll(row.index, $event)"
          @keydown.meta.a.prevent="handleSelectAll(row.index, $event)"
          @mouseup="handleMouseUp(row.index, $event)"
        />
      </template>
      <div
        v-else
        :ref="el => setBlockRef(el, row.index)"
        class="block-content"
        :data-type="row.block.type"
        :contenteditable="!previewMode"
        @input="updateBlock(row.index)"
        @focus="onBlockFocus(row.index)"
        @blur="handleBlur"
        @contextmenu.prevent="onBlockContextMenu(row.index, $event)"
        @keydown.enter.prevent="handleEnter(row.index, $event)"
        @keydown.backspace="handleBackspace(row.index, $event)"
        @keydown.up="moveFocus(row.index, -1, $event)"
        @keydown.down="moveFocus(row.index, 1, $event)"
        @keydown="handleKeydown(row.index, $event)"
        @keydown.ctrl.a.prevent="handleSelectAll(row.index, $event)"
        @keydown.meta.a.prevent="handleSelectAll(row.index, $event)"
        @mouseup="handleMouseUp(row.index, $event)"
      />
      
      <div class="block-actions">
        <el-dropdown trigger="click" @command="(cmd: string) => handleCommand(cmd, row.index)">
          <el-icon class="action-icon" @click.stop><MoreFilled /></el-icon>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="heading" :disabled="previewMode">
                <el-icon><Top /></el-icon> 大标题 <span class="shortcut">Ctrl+1</span>
              </el-dropdown-item>
              <el-dropdown-item command="subheading" :disabled="previewMode">
                <el-icon><Rank /></el-icon> 小标题 <span class="shortcut">Ctrl+2</span>
              </el-dropdown-item>
              <el-dropdown-item command="quote" :disabled="previewMode">
                <el-icon><ChatDotRound /></el-icon> 引用 <span class="shortcut">Ctrl+3</span>
              </el-dropdown-item>
              <el-dropdown-item command="list" :disabled="previewMode">
                <el-icon><List /></el-icon> 列表 <span class="shortcut">Ctrl+4</span>
              </el-dropdown-item>
              <el-dropdown-item command="code" :disabled="previewMode">
                <el-icon><Operation /></el-icon> 代码块 <span class="shortcut">Ctrl+5</span>
              </el-dropdown-item>
              <el-dropdown-item command="divider" :disabled="previewMode">
                <el-icon><Minus /></el-icon> 分割线 <span class="shortcut">Ctrl+6</span>
              </el-dropdown-item>
              <el-dropdown-item divided command="paragraph" :disabled="previewMode">
                <el-icon><Document /></el-icon> 正文 <span class="shortcut">Ctrl+0</span>
              </el-dropdown-item>
              <el-dropdown-item command="moveUp" :disabled="!canMoveUpForToolbar(row.index)">
                <el-icon><ArrowUp /></el-icon> 上移 <span class="shortcut">Ctrl+Shift+↑</span>
              </el-dropdown-item>
              <el-dropdown-item command="moveDown" :disabled="!canMoveDownForToolbar(row.index)">
                <el-icon><ArrowDown /></el-icon> 下移 <span class="shortcut">Ctrl+Shift+↓</span>
              </el-dropdown-item>
              <el-dropdown-item divided command="delete" class="delete-item">
                <el-icon><Delete /></el-icon> 删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

      <div
        v-if="virtualListReady"
        class="virtual-pad virtual-pad-bottom"
        :style="{ height: virtualBottomPad + 'px' }"
        aria-hidden="true"
      />
    </div>
    
    <!-- 右键快捷菜单 -->
    <Teleport to="body">
      <Transition name="context-menu">
        <div
          v-show="contextMenu.visible"
          ref="contextMenuRef"
          class="context-menu"
          :style="contextMenuStyle"
          @mousedown.prevent
          @click.stop
        >
          <div class="context-menu-section">
            <button type="button" class="context-item" :disabled="!canUndo" @click="handleContextAction('undo')">
              <el-icon><RefreshLeft /></el-icon>
              <span>撤销</span>
              <span class="shortcut">Ctrl+Z</span>
            </button>
            <button type="button" class="context-item" :disabled="!canRedo" @click="handleContextAction('redo')">
              <el-icon><RefreshRight /></el-icon>
              <span>重做</span>
              <span class="shortcut">Ctrl+Y</span>
            </button>
          </div>
          <div v-if="!previewMode" class="context-menu-divider" />
          <div v-if="!previewMode" class="context-menu-section">
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'heading' }" @click="handleContextAction('heading')">
              <el-icon><Top /></el-icon>
              <span>大标题</span>
              <span class="shortcut">Ctrl+1</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'subheading' }" @click="handleContextAction('subheading')">
              <el-icon><Rank /></el-icon>
              <span>小标题</span>
              <span class="shortcut">Ctrl+2</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'quote' }" @click="handleContextAction('quote')">
              <el-icon><ChatDotRound /></el-icon>
              <span>引用</span>
              <span class="shortcut">Ctrl+3</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'list' }" @click="handleContextAction('list')">
              <el-icon><List /></el-icon>
              <span>列表</span>
              <span class="shortcut">Ctrl+4</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'code' }" @click="handleContextAction('code')">
              <el-icon><Operation /></el-icon>
              <span>代码块</span>
              <span class="shortcut">Ctrl+5</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'divider' }" @click="handleContextAction('divider')">
              <el-icon><Minus /></el-icon>
              <span>分割线</span>
              <span class="shortcut">Ctrl+6</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && modelValue[contextMenu.blockIndex]?.type === 'paragraph' }" @click="handleContextAction('paragraph')">
              <el-icon><Document /></el-icon>
              <span>正文</span>
              <span class="shortcut">Ctrl+0</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item ai-item" @click="handleContextAction('polish')">
              <el-icon><Brush /></el-icon>
              <span>AI 润色</span>
            </button>
          </div>
          <div v-if="!previewMode" class="context-menu-divider" />
          <div v-if="!previewMode" class="context-menu-section">
            <button type="button" class="context-item" :class="{ active: contextBlock && isFormatActive(contextMenu.blockIndex, 'bold') }" @click="handleContextAction('formatBold')">
              <span class="fmt-bold">B</span>
              <span>加粗</span>
              <span class="shortcut">Ctrl+B</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && isFormatActive(contextMenu.blockIndex, 'italic') }" @click="handleContextAction('formatItalic')">
              <span class="fmt-italic">I</span>
              <span>斜体</span>
              <span class="shortcut">Ctrl+I</span>
            </button>
            <button type="button" class="context-item" :class="{ active: contextBlock && isFormatActive(contextMenu.blockIndex, 'underline') }" @click="handleContextAction('formatUnderline')">
              <span class="fmt-underline">U</span>
              <span>下划线</span>
              <span class="shortcut">Ctrl+U</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button
              type="button"
              class="context-item"
              :disabled="!canMoveUpForToolbar(contextMenu.blockIndex)"
              @click="handleContextAction('moveUp')"
            >
              <el-icon><ArrowUp /></el-icon>
              <span>上移块</span>
              <span class="shortcut">Ctrl+Shift+↑</span>
            </button>
            <button
              type="button"
              class="context-item"
              :disabled="!canMoveDownForToolbar(contextMenu.blockIndex)"
              @click="handleContextAction('moveDown')"
            >
              <el-icon><ArrowDown /></el-icon>
              <span>下移块</span>
              <span class="shortcut">Ctrl+Shift+↓</span>
            </button>
          </div>
          <div v-if="previewMode" class="context-menu-divider" />
          <div v-if="previewMode" class="context-menu-section">
            <button type="button" class="context-item" :disabled="contextMenu.blockIndex < 0" @click="handleContextAction('editText')">
              <el-icon><EditPen /></el-icon>
              <span>编辑文字…</span>
              <span class="shortcut">E</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item" @click="handleContextAction('insertAbove')">
              <el-icon><Plus /></el-icon>
              <span>在上方插入块</span>
            </button>
            <button type="button" class="context-item" @click="handleContextAction('insertBelow')">
              <el-icon><Plus /></el-icon>
              <span>在下方插入块</span>
            </button>
          </div>
          <div class="context-menu-divider" />
          <div class="context-menu-section">
            <button type="button" class="context-item danger" :disabled="modelValue.length <= 1" @click="handleContextAction('delete')">
              <el-icon><Delete /></el-icon>
              <span>删除块</span>
              <span class="shortcut">Ctrl+Shift+D</span>
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

    <!-- 预览模式：弹窗编辑文字（不进入 contenteditable） -->
    <el-dialog v-model="previewEditDialogVisible" title="编辑文字" width="640px" append-to-body>
      <el-input
        v-model="previewEditDialogText"
        type="textarea"
        :autosize="{ minRows: 6, maxRows: 18 }"
        placeholder="在预览模式下修改当前块的文本…"
      />
      <template #footer>
        <el-button @click="previewEditDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="applyPreviewTextEdit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import type { Block } from '@/stores/project'
import { ElMessage } from 'element-plus'
import { Plus, MoreFilled, Top, ChatDotRound, List, Document, Delete, EditPen, Brush, Rank, Operation, Minus, RefreshLeft, RefreshRight, DocumentCopy, Scissor, Close, MagicStick, Picture, ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const props = defineProps<{
  modelValue: Block[]
  focusMode?: boolean
  /** 预览：不可在块内直接编辑；可调整结构（插入/移动/删除块）、撤销重做、多选复制剪切、AI 等 */
  previewMode?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Block[]): void
  (e: 'polish', payload: { index: number; text: string }): void
  (e: 'polish-selected', payload: { indices: number[]; text: string }): void
  (e: 'revise-selected', payload: { indices: number[]; text: string }): void
  (e: 'expand-selected', payload: { indices: number[]; text: string }): void
  (e: 'generate-image-for-selection', payload: { indices: number[]; text: string }): void
  (e: 'toggleFocusMode'): void
  (e: 'replace', payload: { index: number; oldText: string; newText: string }): void
  /** 用户正在编辑（不等待防抖后的 v-model 同步），用于立即标记未保存 */
  (e: 'content-dirty'): void
}>()

/** 输入同步到父组件：防抖，减少整页与侧栏随每次按键重绘 */
let contentEmitTimer: ReturnType<typeof setTimeout> | null = null
const CONTENT_EMIT_DEBOUNCE_MS = 100
/** 块数较少时每次输入从 DOM 拉全量，避免防抖窗口内多块不同步 */
const FULL_DOM_SNAPSHOT_MAX_BLOCKS = 96

function clearContentEmitTimer() {
  if (contentEmitTimer) {
    clearTimeout(contentEmitTimer)
    contentEmitTimer = null
  }
}

/** 结构变更、撤销重做等须立即同步 */
function emitContentUpdateNow(blocks: Block[]) {
  clearContentEmitTimer()
  emit('update:modelValue', blocks)
}

/** 纯文本输入：防抖后同步 */
function scheduleContentUpdate(blocks: Block[]) {
  clearContentEmitTimer()
  contentEmitTimer = setTimeout(() => {
    contentEmitTimer = null
    emit('update:modelValue', blocks)
  }, CONTENT_EMIT_DEBOUNCE_MS)
}

// ---------- 虚拟列表：块数较多时只挂载可视区域 + 上下缓冲 ----------
const VIRTUAL_THRESHOLD = 28
const VIRTUAL_OVERSCAN = 8
const virtualEnabled = computed(() => props.modelValue.length >= VIRTUAL_THRESHOLD)

const scrollEl = ref<HTMLElement | null>(null)
const virtualStart = ref(0)
const virtualEnd = ref(0)
/** 与 modelValue 对齐；0 表示尚未测量，用 estimate */
const measuredHeights = ref<number[]>([])
const blockOffsets = ref<number[]>([])
const wrapperResizeObservers = new Map<number, ResizeObserver>()
let scrollViewportRo: ResizeObserver | null = null
let virtualScrollRaf: number | null = null
/** 上一帧 scrollTop，用于快速滚动时加大 overscan */
const lastScrollTopForVirtual = ref(0)

// ---------- 滚动节流控制（~60fps） ----------
let lastVirtualUpdateTime = 0
const VIRTUAL_THROTTLE_MS = 16
/** 用户主动滚动标记：区分用户滚动与程序滚动 */
const isUserScrolling = ref(false)
let userScrollTimeout: number | null = null
function markUserScrolling() {
  isUserScrolling.value = true
  if (userScrollTimeout) window.clearTimeout(userScrollTimeout)
  userScrollTimeout = window.setTimeout(() => {
    isUserScrolling.value = false
  }, 150)
}
/** 防止 updateVirtualWindow 重入锁 */
let isUpdatingVirtualWindow = false
/** 是否有待处理的虚拟窗口更新 */
let pendingVirtualUpdate = false
/** 程序滚动中暂停虚拟渲染 */
let isProgramScrolling = false
let programScrollTimeout: number | null = null

function vnodeRefToHTMLElement(el: unknown): HTMLElement | null {
  if (el == null) return null
  if (el instanceof HTMLElement) return el
  if (typeof el === 'object' && el !== null && '$el' in el) {
    const inner = (el as { $el?: unknown }).$el
    return inner instanceof HTMLElement ? inner : null
  }
  return null
}

function estimateBlockHeight(block: Block): number {
  const len = (block.content || '').length
  // 提高长文估计高度，避免 offset 总长远小于真实 scrollHeight 时虚拟窗口严重错位、快速滚动长时间空白
  const lineSoft = Math.min(2400, Math.max(0, len) * 0.38 + Math.sqrt(Math.max(0, len)) * 3)
  const lineTight = Math.min(400, Math.max(0, len) * 0.2)
  switch (block.type) {
    case 'heading':
      return Math.round(52 + lineTight)
    case 'subheading':
      return Math.round(46 + lineTight)
    case 'code':
      return Math.round(64 + Math.min(480, len * 0.35))
    case 'quote':
      return Math.round(48 + lineSoft)
    case 'list':
      return Math.round(44 + lineSoft)
    case 'image':
      return block.props?.src ? 228 : 88
    case 'divider':
      return 36
    default:
      return Math.round(44 + lineSoft)
  }
}

function getHeightForIndex(i: number): number {
  const m = measuredHeights.value[i]
  if (m != null && m > 0) return m
  const b = props.modelValue[i]
  return b ? estimateBlockHeight(b) : 48
}

function rebuildBlockOffsets() {
  const n = props.modelValue.length
  const arr = new Array<number>(n + 1)
  arr[0] = 0
  for (let i = 0; i < n; i++) {
    arr[i + 1] = arr[i] + getHeightForIndex(i)
  }
  blockOffsets.value = arr
}

/** 第一个满足 offsets[i+1] > st 的 i；若全部在上方则为 n */
function virtualFirstRowAfterScroll(offsets: number[], n: number, st: number): number {
  let lo = 0
  let hi = n
  while (lo < hi) {
    const mid = (lo + hi) >>> 1
    if (offsets[mid + 1] <= st) lo = mid + 1
    else hi = mid
  }
  return lo
}

/** 最后一个满足 offsets[i] < bottom 的索引，且 i >= start */
function virtualLastVisibleRow(offsets: number[], n: number, start: number, bottom: number): number {
  let lo = start
  let hi = n
  while (lo < hi) {
    const mid = (lo + hi) >>> 1
    if (offsets[mid] < bottom) lo = mid + 1
    else hi = mid
  }
  return Math.max(start, lo - 1)
}

function updateVirtualWindow() {
  if (!virtualEnabled.value || !scrollEl.value) return
  // 程序滚动期间跳过虚拟窗口更新（由 scrollToBlockIndex 的定时器恢复后统一更新）
  if (isProgramScrolling) return
  // 重入锁：防止循环触发
  if (isUpdatingVirtualWindow) {
    pendingVirtualUpdate = true
    return
  }
  isUpdatingVirtualWindow = true
  try {
    const el = scrollEl.value
    const stRaw = el.scrollTop
    const vh = el.clientHeight || 1
    const n = props.modelValue.length
    const offsets = blockOffsets.value
    if (n === 0 || offsets.length !== n + 1) {
      virtualStart.value = 0
      virtualEnd.value = -1
      return
    }
    const modelTotal = offsets[n] ?? 0
    const scrollRange = Math.max(1, el.scrollHeight - vh)
    const modelScrollRange = Math.max(1, modelTotal - vh)
    // DOM 总高与估计 offset 不一致时（常见于未测量块低估），按滚动比例映射到模型坐标，避免窗口卡在错误区间
    const stModel = (stRaw / scrollRange) * modelScrollRange
    const bottomModel = stModel + vh

    let start = virtualFirstRowAfterScroll(offsets, n, stModel)
    if (start >= n) start = Math.max(0, n - 1)
    let end = virtualLastVisibleRow(offsets, n, start, bottomModel)
    if (end >= n) end = n - 1

    let overscan = VIRTUAL_OVERSCAN
    const delta = stRaw - lastScrollTopForVirtual.value
    lastScrollTopForVirtual.value = stRaw
    if (Math.abs(delta) > vh * 0.35) {
      overscan += Math.min(28, Math.floor(Math.abs(delta) / Math.max(40, vh * 0.2)))
    }

    start = Math.max(0, start - overscan)
    end = Math.min(n - 1, end + overscan)

    // 正在编辑的块必须始终在挂载范围内，否则 contenteditable 被卸载会导致焦点乱跳、无法输入
    const fi = focusedIndex.value
    if (fi >= 0 && fi < n) {
      if (fi < start) start = Math.max(0, fi - overscan)
      if (fi > end) end = Math.min(n - 1, fi + overscan)
    }

    virtualStart.value = start
    virtualEnd.value = end
  } finally {
    isUpdatingVirtualWindow = false
    // 如果有待处理的更新，在下一个事件循环中执行
    if (pendingVirtualUpdate) {
      pendingVirtualUpdate = false
      nextTick(updateVirtualWindow)
    }
  }
}

function scheduleVirtualScrollUpdate() {
  if (virtualScrollRaf != null) return
  virtualScrollRaf = requestAnimationFrame(() => {
    virtualScrollRaf = null
    updateVirtualWindow()
  })
}

function onBlockListScroll() {
  if (!virtualEnabled.value) return
  // 程序滚动期间暂停虚拟渲染，避免卡顿
  if (isProgramScrolling) return
  markUserScrolling()
  // 节流控制：避免频繁更新
  const now = performance.now()
  if (now - lastVirtualUpdateTime < VIRTUAL_THROTTLE_MS) {
    scheduleVirtualScrollUpdate()
    return
  }
  lastVirtualUpdateTime = now
  // 同步更新窗口，避免仅依赖 RAF 时快速惯性滚动多帧落在错误区间、迟迟不出现块
  updateVirtualWindow()
}

const virtualListReady = computed(() => {
  if (!virtualEnabled.value) return false
  const n = props.modelValue.length
  return scrollEl.value != null && blockOffsets.value.length === n + 1 && n > 0
})

function bindScrollEl(el: unknown) {
  scrollViewportRo?.disconnect()
  scrollViewportRo = null
  scrollEl.value = vnodeRefToHTMLElement(el)
  if (!scrollEl.value) return
  lastScrollTopForVirtual.value = scrollEl.value.scrollTop
  scrollViewportRo = new ResizeObserver(() => {
    if (virtualEnabled.value) {
      rebuildBlockOffsets()
      updateVirtualWindow()
    }
  })
  scrollViewportRo.observe(scrollEl.value)
  if (virtualEnabled.value && props.modelValue.length > 0) {
    syncMeasuredHeightsLength()
    rebuildBlockOffsets()
    requestAnimationFrame(() => {
      updateVirtualWindow()
      initBlockContents()
    })
  }
}

watch(virtualEnabled, (enabled) => {
  if (!enabled || !scrollEl.value || props.modelValue.length === 0) return
  syncMeasuredHeightsLength()
  rebuildBlockOffsets()
  nextTick(() => {
    updateVirtualWindow()
    initBlockContents()
  })
})

const virtualTopPad = computed(() => {
  if (!virtualListReady.value) return 0
  const o = blockOffsets.value
  return o[virtualStart.value] ?? 0
})

const virtualBottomPad = computed(() => {
  if (!virtualListReady.value) return 0
  const n = props.modelValue.length
  const o = blockOffsets.value
  if (!n || o.length !== n + 1) return 0
  const total = o[n] ?? 0
  const after = o[virtualEnd.value + 1] ?? total
  return Math.max(0, total - after)
})

const displayedRows = computed(() => {
  const blocks = props.modelValue
  if (!blocks.length) return [] as { block: Block; index: number }[]
  if (!virtualEnabled.value) {
    return blocks.map((block, index) => ({ block, index }))
  }
  if (!virtualListReady.value) {
    const cap = Math.min(blocks.length, 40)
    const out: { block: Block; index: number }[] = []
    for (let i = 0; i < cap; i++) {
      const b = blocks[i]
      if (!b) continue
      out.push({ block: b, index: i })
    }
    return out
  }
  const s = virtualStart.value
  const e = virtualEnd.value
  if (e < s) return []
  const out: { block: Block; index: number }[] = []
  for (let i = s; i <= e; i++) {
    const b = blocks[i]
    if (!b) continue
    out.push({ block: b, index: i })
  }
  return out
})

function syncMeasuredHeightsLength() {
  const n = props.modelValue.length
  const cur = measuredHeights.value
  if (cur.length === n) return
  const next = cur.slice(0, n)
  while (next.length < n) next.push(0)
  measuredHeights.value = next
}

function scrollToBlockIndex(index: number, align: 'start' | 'nearest' = 'nearest', behavior: ScrollBehavior = 'auto', force = false) {
  if (!virtualEnabled.value || !scrollEl.value) return
  // 如果正在用户主动滚动，且不是强制滚动，则跳过
  if (!force && isUserScrolling.value) return
  rebuildBlockOffsets()
  const el = scrollEl.value
  const offsets = blockOffsets.value
  const n = props.modelValue.length
  if (index < 0 || index >= n || offsets.length !== n + 1) return
  const top = offsets[index]
  const h = getHeightForIndex(index)
  const vh = el.clientHeight
  const st = el.scrollTop
  let targetSt = st
  if (align === 'start') {
    targetSt = Math.max(0, top - 12)
  } else {
    if (top < st) targetSt = Math.max(0, top - 12)
    else if (top + h > st + vh) targetSt = Math.max(0, top + h - vh + 12)
  }
  // 如果已经在视口内，不滚动
  if (targetSt === st) {
    updateVirtualWindow()
    return
  }
  // 程序滚动前清除用户滚动标记，避免被自己的滚动事件阻塞
  isUserScrolling.value = false
  if (userScrollTimeout) {
    window.clearTimeout(userScrollTimeout)
    userScrollTimeout = null
  }
  // 标记程序滚动中，暂停虚拟渲染以避免卡顿
  isProgramScrolling = true
  if (programScrollTimeout) {
    window.clearTimeout(programScrollTimeout)
    programScrollTimeout = null
  }
  // 滚动动画结束后恢复虚拟渲染
  const scrollDuration = behavior === 'smooth' ? 300 : 50
  programScrollTimeout = window.setTimeout(() => {
    isProgramScrolling = false
    updateVirtualWindow()
  }, scrollDuration + 50)

  if (behavior === 'smooth') el.scrollTo({ top: targetSt, behavior })
  else el.scrollTop = targetSt
  // 滚动期间不立即更新虚拟窗口，等滚动完成后再更新
}

function setBlockWrapperRef(el: unknown, index: number) {
  const htmlEl = vnodeRefToHTMLElement(el)
  if (!htmlEl) {
    wrapperResizeObservers.get(index)?.disconnect()
    wrapperResizeObservers.delete(index)
    return
  }
  const ro = new ResizeObserver(() => {
    const h = Math.ceil(htmlEl.getBoundingClientRect().height)
    if (h < 8) return
    const cur = measuredHeights.value[index]
    if (cur === h) return
    const copy = [...measuredHeights.value]
    while (copy.length <= index) copy.push(0)
    copy[index] = h
    measuredHeights.value = copy
    rebuildBlockOffsets()
    scheduleVirtualScrollUpdate()
  })
  ro.observe(htmlEl)
  wrapperResizeObservers.set(index, ro)
}

const focusedIndex = ref(-1)
const blockRefs = ref<Map<number, HTMLElement>>(new Map())
let focusBlurTimer: ReturnType<typeof setTimeout> | null = null
/** 当前显示快捷栏的块索引，-1 为不显示。悬停 3s 或选中 3s 后赋值 */
const toolbarVisibleIndex = ref(-1)
/** 右键快捷菜单状态 */
const contextMenu = ref({ visible: false, x: 0, y: 0, blockIndex: -1 })
const contextMenuRef = ref<HTMLElement | null>(null)
const contextBlock = computed(() =>
  contextMenu.value.visible && contextMenu.value.blockIndex >= 0 && props.modelValue[contextMenu.value.blockIndex]
    ? props.modelValue[contextMenu.value.blockIndex]
    : null
)

// 动态计算右键菜单位置，确保不超出屏幕
const contextMenuStyle = computed(() => {
  const menuWidth = 280 // 菜单最大宽度
  const menuHeight = 400 // 预估菜单高度（滚动区域）
  const padding = 10 // 屏幕边缘留白

  let x = contextMenu.value.x
  let y = contextMenu.value.y

  // 获取屏幕尺寸
  const screenWidth = window.innerWidth
  const screenHeight = window.innerHeight

  // 水平方向：如果超出右边界，则向左显示
  if (x + menuWidth + padding > screenWidth) {
    x = screenWidth - menuWidth - padding
  }

  // 垂直方向：如果超出下边界，则向上显示
  if (y + menuHeight + padding > screenHeight) {
    y = screenHeight - menuHeight - padding
    // 如果向上显示也会超出上边界，则显示在屏幕顶部附近
    if (y < padding) {
      y = padding
    }
  }

  // 确保不会显示在屏幕左上角之外
  x = Math.max(padding, x)
  y = Math.max(padding, y)

  return {
    left: x + 'px',
    top: y + 'px'
  }
})

// 动态计算斜杠菜单位置
const slashMenuStyle = computed(() => {
  const menuWidth = 320 // 菜单最大宽度
  const menuHeight = 350 // 预估菜单高度
  const padding = 10 // 屏幕边缘留白

  let x = slashMenuPosition.value.x
  let y = slashMenuPosition.value.y

  // 获取屏幕尺寸
  const screenWidth = window.innerWidth
  const screenHeight = window.innerHeight

  // 水平方向：如果超出右边界，则向左显示
  if (x + menuWidth + padding > screenWidth) {
    x = Math.max(padding, screenWidth - menuWidth - padding)
  }

  // 垂直方向：优先向下显示，如果超出下边界则向上显示
  if (y + menuHeight + padding > screenHeight) {
    // 向上显示（在光标上方）
    y = Math.max(padding, y - menuHeight - 40) // 40是块的高度
  }

  // 确保不会显示在屏幕之外
  x = Math.max(padding, x)
  y = Math.max(padding, y)

  return {
    left: x + 'px',
    top: y + 'px'
  }
})
const isFocusMode = ref(props.focusMode || false)
const TOOLBAR_DELAY_MS = 3000
const TOOLBAR_HIDE_DELAY_MS = 300
let hoverTimer: ReturnType<typeof setTimeout> | null = null
let selectionTimer: ReturnType<typeof setTimeout> | null = null
let leaveTimer: ReturnType<typeof setTimeout> | null = null

// ========== 斜杠命令菜单 ==========
const slashMenuVisible = ref(false)
const slashMenuPosition = ref({ x: 0, y: 0 })
const selectedSlashIndex = ref(0)
const slashQuery = ref('')
const currentSlashBlockIndex = ref(-1)

const slashCommands = [
  { id: 'heading', label: '大标题', icon: 'Top', shortcut: 'Ctrl+1', type: 'heading' },
  { id: 'subheading', label: '小标题', icon: 'Rank', shortcut: 'Ctrl+2', type: 'subheading' },
  { id: 'quote', label: '引用', icon: 'ChatDotRound', shortcut: 'Ctrl+3', type: 'quote' },
  { id: 'list', label: '列表', icon: 'List', shortcut: 'Ctrl+4', type: 'list' },
  { id: 'code', label: '代码块', icon: 'Operation', shortcut: 'Ctrl+5', type: 'code' },
  { id: 'divider', label: '分割线', icon: 'Minus', shortcut: 'Ctrl+6', type: 'divider' },
  { id: 'paragraph', label: '正文', icon: 'Document', shortcut: 'Ctrl+0', type: 'paragraph' },
]

const filteredSlashCommands = computed(() => {
  if (!slashQuery.value) return slashCommands
  const query = slashQuery.value.toLowerCase()
  return slashCommands.filter(cmd =>
    cmd.label.toLowerCase().includes(query) ||
    cmd.id.toLowerCase().includes(query)
  )
})

function showSlashMenu(index: number, rect: DOMRect) {
  currentSlashBlockIndex.value = index
  slashMenuPosition.value = {
    x: rect.left,
    y: rect.bottom + 8
  }
  slashMenuVisible.value = true
  selectedSlashIndex.value = 0
  slashQuery.value = ''
}

function hideSlashMenu() {
  slashMenuVisible.value = false
  slashQuery.value = ''
  currentSlashBlockIndex.value = -1
}

function applySlashCommand(commandIndex: number, blockIndex?: number) {
  const commands = filteredSlashCommands.value
  if (commandIndex < 0 || commandIndex >= commands.length) return

  const command = commands[commandIndex]
  const targetIndex = blockIndex !== undefined ? blockIndex : currentSlashBlockIndex.value
  if (targetIndex < 0) return

  // 清除斜杠命令文本
  const el = blockRefs.value.get(targetIndex)
  if (el) {
    const text = el.textContent || ''
    const newText = text.replace(/\/[^\s]*$/, '').trim()
    el.textContent = newText
    updateBlock(targetIndex)
  }

  handleCommand(command.type, targetIndex)
  hideSlashMenu()
}

// ========== 多选块功能 ==========
const selectedBlocks = ref<Set<number>>(new Set())
const isMultiSelectMode = ref(false)

/** 多选工具栏「上移/下移」用的锚点下标（多选时任意成员均可，内部按整体选区处理） */
const multiToolbarAnchorIndex = computed(() => {
  if (selectedBlocks.value.size === 0) return 0
  return Math.min(...Array.from(selectedBlocks.value))
})

const selectedContiguousMeta = computed(() => {
  const sorted = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  if (sorted.length === 0) {
    return { contiguous: true, sorted: [] as number[], start: 0, end: 0 }
  }
  if (sorted.length === 1) {
    return { contiguous: true, sorted, start: sorted[0], end: sorted[0] }
  }
  let contiguous = true
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) {
      contiguous = false
      break
    }
  }
  return { contiguous, sorted, start: sorted[0], end: sorted[sorted.length - 1] }
})

const canMoveUpMultiToolbar = computed(() => {
  if (selectedBlocks.value.size < 2) return false
  const { contiguous, start } = selectedContiguousMeta.value
  if (!contiguous) return false
  return start > 0
})

const canMoveDownMultiToolbar = computed(() => {
  if (selectedBlocks.value.size < 2) return false
  const n = props.modelValue.length
  const { contiguous, end } = selectedContiguousMeta.value
  if (!contiguous) return false
  return end < n - 1
})

function isSelectionContiguous(): boolean {
  const sorted = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  if (sorted.length <= 1) return true
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i] !== sorted[i - 1] + 1) return false
  }
  return true
}

function canMoveUpForToolbar(index: number): boolean {
  const n = props.modelValue.length
  if (n <= 1) return false
  if (selectedBlocks.value.size > 1) {
    if (!isSelectionContiguous()) return false
    const sorted = Array.from(selectedBlocks.value).sort((a, b) => a - b)
    return sorted[0] > 0
  }
  if (selectedBlocks.value.size === 1) {
    const i = Array.from(selectedBlocks.value)[0]
    return i > 0
  }
  return index > 0
}

function canMoveDownForToolbar(index: number): boolean {
  const n = props.modelValue.length
  if (n <= 1) return false
  if (selectedBlocks.value.size > 1) {
    if (!isSelectionContiguous()) return false
    const sorted = Array.from(selectedBlocks.value).sort((a, b) => a - b)
    return sorted[sorted.length - 1] < n - 1
  }
  if (selectedBlocks.value.size === 1) {
    const i = Array.from(selectedBlocks.value)[0]
    return i < n - 1
  }
  return index < n - 1
}

/**
 * 移动块：无多选或单选时移动当前块；多选连续区间时整体移动。
 * @param keydownIndex 单块移动时的下标（工具栏点击或光标所在块）
 */
function tryMoveBlocks(delta: -1 | 1, keydownIndex: number) {
  const n = props.modelValue.length
  if (n <= 1) return

  const sel = selectedBlocks.value
  if (sel.size > 1) {
    const sorted = Array.from(sel).sort((a, b) => a - b)
    for (let i = 1; i < sorted.length; i++) {
      if (sorted[i] !== sorted[i - 1] + 1) {
        ElMessage.warning('请先选中连续的块再整体移动')
        return
      }
    }
    const start = sorted[0]
    const end = sorted[sorted.length - 1]
    if (delta === -1 && start === 0) return
    if (delta === 1 && end >= n - 1) return
    const newBlocks = [...props.modelValue]
    const chunk = newBlocks.splice(start, end - start + 1)
    if (delta === -1) {
      newBlocks.splice(start - 1, 0, ...chunk)
    } else {
      newBlocks.splice(start + 1, 0, ...chunk)
    }
    emitContentUpdateNow(newBlocks)
    saveHistory()
    const newStart = delta === -1 ? start - 1 : start + 1
    const newEnd = delta === -1 ? end - 1 : end + 1
    selectedBlocks.value.clear()
    for (let i = newStart; i <= newEnd; i++) {
      selectedBlocks.value.add(i)
    }
    isMultiSelectMode.value = true
    focusedIndex.value = newStart
    nextTick(() => {
      const el = blockRefs.value.get(newStart)
      if (el) {
        el.focus({ preventScroll: true })
        scrollElementIntoView(el)
      }
    })
    return
  }

  const idx = sel.size === 1 ? Array.from(sel)[0] : keydownIndex
  if (idx < 0 || idx >= n) return
  const newIdx = idx + delta
  if (newIdx < 0 || newIdx >= n) return

  const newBlocks = [...props.modelValue]
  const [item] = newBlocks.splice(idx, 1)
  newBlocks.splice(newIdx, 0, item)
  emitContentUpdateNow(newBlocks)
  saveHistory()
  focusedIndex.value = newIdx
  if (sel.size === 1) {
    selectedBlocks.value.clear()
    selectedBlocks.value.add(newIdx)
  }
  nextTick(() => {
    const el = blockRefs.value.get(newIdx)
    if (el) {
      el.focus({ preventScroll: true })
      scrollElementIntoView(el)
    }
  })
}

function toggleBlockSelection(index: number, event?: MouseEvent) {
  if (event) {
    if (event.ctrlKey || event.metaKey) {
      // Ctrl/Cmd + 点击：切换选择
      if (selectedBlocks.value.has(index)) {
        selectedBlocks.value.delete(index)
      } else {
        selectedBlocks.value.add(index)
      }
      isMultiSelectMode.value = true
    } else if (event.shiftKey && selectedBlocks.value.size > 0) {
      // Shift + 点击：范围选择
      const lastSelected = Math.max(...selectedBlocks.value)
      const start = Math.min(lastSelected, index)
      const end = Math.max(lastSelected, index)
      for (let i = start; i <= end; i++) {
        selectedBlocks.value.add(i)
      }
      isMultiSelectMode.value = true
    } else {
      // 普通点击：清除其他选择，只选当前
      selectedBlocks.value.clear()
      selectedBlocks.value.add(index)
      isMultiSelectMode.value = false
    }
  } else {
    selectedBlocks.value.clear()
    selectedBlocks.value.add(index)
    isMultiSelectMode.value = false
  }
}

function clearBlockSelection() {
  selectedBlocks.value.clear()
  isMultiSelectMode.value = false
}

function selectAllBlocks() {
  selectedBlocks.value.clear()
  for (let i = 0; i < props.modelValue.length; i++) {
    selectedBlocks.value.add(i)
  }
  isMultiSelectMode.value = true
}

function handleSelectAll(index: number, event: Event) {
  if (props.previewMode) {
    event.preventDefault()
    selectAllBlocks()
    return
  }
  const el = blockRefs.value.get(index)
  if (!el) return

  const selection = window.getSelection()
  if (!selection) return

  const range = document.createRange()
  range.selectNodeContents(el)
  selection.removeAllRanges()
  selection.addRange(range)

  // 如果已经在全选状态，则跨块选择
  const text = selection.toString()
  const elText = el.textContent || ''
  if (text === elText && props.modelValue.length > 1) {
    selectAllBlocks()
  }
}

function handleMouseUp(index: number, event: MouseEvent) {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return

  // 检查是否是跨块选择
  const range = selection.getRangeAt(0)
  let startBlock = -1
  let endBlock = -1

  for (const [idx, el] of blockRefs.value) {
    if (el && range.intersectsNode(el)) {
      if (startBlock === -1) startBlock = idx
      endBlock = idx
    }
  }

  if (startBlock !== -1 && endBlock !== -1 && startBlock !== endBlock) {
    // 跨块选择
    selectedBlocks.value.clear()
    for (let i = startBlock; i <= endBlock; i++) {
      selectedBlocks.value.add(i)
    }
    isMultiSelectMode.value = true
  } else if (event.ctrlKey || event.metaKey || event.shiftKey) {
    toggleBlockSelection(index, event)
  }
}

// ========== 撤销重做系统 ==========
const history = ref<Block[][]>([])
const historyIndex = ref(-1)
const maxHistorySize = 50
let isUndoing = false

const canUndo = computed(() => historyIndex.value > 0)
const canRedo = computed(() => historyIndex.value >= 0 && historyIndex.value < history.value.length - 1)

// 保存历史状态
function saveHistory() {
  if (isUndoing) return
  
  // 如果当前不是最新状态，删除当前之后的历史
  if (historyIndex.value < history.value.length - 1) {
    history.value = history.value.slice(0, historyIndex.value + 1)
  }
  
  // 深拷贝当前内容
  const snapshot = JSON.parse(JSON.stringify(props.modelValue))
  history.value.push(snapshot)
  
  // 限制历史记录大小
  if (history.value.length > maxHistorySize) {
    history.value.shift()
  } else {
    historyIndex.value++
  }
}

// 撤销
function undo() {
  if (historyIndex.value > 0) {
    isUndoing = true
    historyIndex.value--
    const snapshot = history.value[historyIndex.value]
    emitContentUpdateNow(JSON.parse(JSON.stringify(snapshot)))
    nextTick(() => {
      initBlockContents()
      isUndoing = false
    })
  }
}

// 重做
function redo() {
  if (historyIndex.value < history.value.length - 1) {
    isUndoing = true
    historyIndex.value++
    const snapshot = history.value[historyIndex.value]
    emitContentUpdateNow(JSON.parse(JSON.stringify(snapshot)))
    nextTick(() => {
      initBlockContents()
      isUndoing = false
    })
  }
}

// 防抖保存历史
let historyTimer: ReturnType<typeof setTimeout> | null = null
function debouncedSaveHistory() {
  if (historyTimer) clearTimeout(historyTimer)
  historyTimer = setTimeout(() => {
    saveHistory()
  }, 750)
}

// 初始化历史
onMounted(() => {
  if (props.modelValue.length > 0) {
    saveHistory()
  }
})

function toggleFocusMode() {
  isFocusMode.value = !isFocusMode.value
  emit('toggleFocusMode')
}

// 初始化块内容
function onBlockContextMenu(index: number, event: MouseEvent) {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    blockIndex: index
  }
}

function onEmptyAreaContextMenu(event: MouseEvent) {
  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
    blockIndex: -1
  }
}

function closeContextMenu() {
  contextMenu.value = { ...contextMenu.value, visible: false }
}

function handleContextAction(action: string) {
  const idx = contextMenu.value.blockIndex
  if (idx < 0 && action !== 'undo' && action !== 'redo') {
    closeContextMenu()
    return
  }
  switch (action) {
    case 'undo':
      undo()
      break
    case 'redo':
      redo()
      break
    case 'heading':
    case 'subheading':
    case 'quote':
    case 'list':
    case 'code':
    case 'divider':
    case 'paragraph':
      handleCommand(action, idx)
      break
    case 'polish':
      emitPolish(idx)
      break
    case 'formatBold':
      applyFormat(idx, 'bold')
      break
    case 'formatItalic':
      applyFormat(idx, 'italic')
      break
    case 'formatUnderline':
      applyFormat(idx, 'underline')
      break
    case 'moveUp':
      tryMoveBlocks(-1, idx)
      break
    case 'moveDown':
      tryMoveBlocks(1, idx)
      break
    case 'editText':
      openPreviewTextEdit(idx)
      break
    case 'insertAbove':
      addBlock(idx - 1)
      nextTick(() => {
        if (props.previewMode) return
        const el = blockRefs.value.get(idx)
        if (el) el.focus()
      })
      break
    case 'insertBelow':
      addBlock(idx >= 0 ? idx : -1)
      break
    case 'delete':
      if (props.modelValue.length > 1) handleCommand('delete', idx)
      break
    default:
      break
  }
  closeContextMenu()
}

onMounted(() => {
  initBlockContents()
  document.addEventListener('selectionchange', onSelectionChange)
  document.addEventListener('click', closeContextMenu)
})

onUnmounted(() => {
  if (focusBlurTimer) {
    clearTimeout(focusBlurTimer)
    focusBlurTimer = null
  }
  document.removeEventListener('selectionchange', onSelectionChange)
  document.removeEventListener('click', closeContextMenu)
  if (hoverTimer) clearTimeout(hoverTimer)
  if (selectionTimer) clearTimeout(selectionTimer)
  if (leaveTimer) clearTimeout(leaveTimer)
  scrollViewportRo?.disconnect()
  scrollViewportRo = null
  wrapperResizeObservers.forEach((ro) => ro.disconnect())
  wrapperResizeObservers.clear()
})

function onBlockMouseEnter(index: number) {
  if (leaveTimer) {
    clearTimeout(leaveTimer)
    leaveTimer = null
  }
  if (selectionTimer) {
    clearTimeout(selectionTimer)
    selectionTimer = null
  }
  if (hoverTimer) clearTimeout(hoverTimer)
  hoverTimer = setTimeout(() => {
    hoverTimer = null
    toolbarVisibleIndex.value = index
  }, TOOLBAR_DELAY_MS)
}

function onBlockMouseLeave() {
  if (hoverTimer) {
    clearTimeout(hoverTimer)
    hoverTimer = null
  }
  if (leaveTimer) clearTimeout(leaveTimer)
  leaveTimer = setTimeout(() => {
    leaveTimer = null
    toolbarVisibleIndex.value = -1
  }, TOOLBAR_HIDE_DELAY_MS)
}

function onSelectionChange() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0) {
    if (selectionTimer) {
      clearTimeout(selectionTimer)
      selectionTimer = null
    }
    toolbarVisibleIndex.value = -1
    return
  }
  const anchor = sel.anchorNode
  if (!anchor || !sel.toString().trim()) {
    if (selectionTimer) {
      clearTimeout(selectionTimer)
      selectionTimer = null
    }
    toolbarVisibleIndex.value = -1
    return
  }
  let blockIndex = -1
  for (const [idx, el] of blockRefs.value) {
    if (el && el.contains(anchor)) {
      blockIndex = idx
      break
    }
  }
  if (blockIndex < 0) {
    if (selectionTimer) clearTimeout(selectionTimer)
    selectionTimer = null
    toolbarVisibleIndex.value = -1
    return
  }
  if (selectionTimer) clearTimeout(selectionTimer)
  selectionTimer = setTimeout(() => {
    selectionTimer = null
    toolbarVisibleIndex.value = blockIndex
  }, TOOLBAR_DELAY_MS)
}

watch(
  () => props.previewMode,
  (on) => {
    if (on) {
      hideSlashMenu()
      nextTick(() => {
        const ae = document.activeElement
        if (ae instanceof HTMLElement) {
          for (const el of blockRefs.value.values()) {
            if (el === ae) {
              ae.blur()
              break
            }
          }
        }
        focusedIndex.value = -1
      })
    } else {
      nextTick(() => initBlockContents())
    }
  }
)

watch(
  () => props.modelValue.length,
  (n, prev) => {
    syncMeasuredHeightsLength()
    if (prev != null && n < prev) {
      for (let i = n; i < prev; i++) {
        wrapperResizeObservers.get(i)?.disconnect()
        wrapperResizeObservers.delete(i)
      }
    }
    nextTick(() => {
      rebuildBlockOffsets()
      updateVirtualWindow()
      initBlockContents()
    })
  }
)

watch([virtualStart, virtualEnd], () => {
  nextTick(() => initBlockContents())
})

function setBlockRef(el: unknown, index: number) {
  if (el) {
    blockRefs.value.set(index, el as HTMLElement)
  } else {
    blockRefs.value.delete(index)
  }
}

function initBlockContents() {
  props.modelValue.forEach((block, index) => {
    const el = blockRefs.value.get(index)
    if (!el) return
    // v-model 防抖期间父级 props 可能落后于 DOM，勿用旧 model 覆盖正在编辑的节点
    if (document.activeElement === el) return
    const raw = block.content || ''
    const hasHtml = /<(b|i|u|strong|em)\b/i.test(raw)
    if (!hasHtml) {
      if (el.textContent !== raw) el.textContent = raw
    } else {
      if (el.innerHTML !== raw) el.innerHTML = raw
    }
  })
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

/** 后端返回的 /static/... 需拼 API 根地址，便于跨端口开发加载图片 */
function resolveImageUrl(src: string): string {
  if (!src) return ''
  if (src.startsWith('http://') || src.startsWith('https://')) return src
  if (src.startsWith('/')) {
    // 避免 ImportMetaEnv 类型缺失导致的 TS 报错
    const base = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'
    const origin = String(base).replace(/\/api\/?$/, '')
    return origin + src
  }
  return src
}

function addBlock(index: number, type: Block['type'] = 'paragraph') {
  const newBlock: Block = {
    id: generateId(),
    type,
    content: '',
    props: {}
  }
  const newBlocks = [...props.modelValue]
  newBlocks.splice(index + 1, 0, newBlock)
  emitContentUpdateNow(newBlocks)
  saveHistory()

  if (!props.previewMode) {
    nextTick(() => {
      const newIndex = index + 1
      let el = blockRefs.value.get(newIndex)
      nextTick(() => {
        el = blockRefs.value.get(newIndex)
        if (el) {
          el.focus({ preventScroll: true })
        }
      })
    })
  }
}

function sanitizeBlockContent(html: string): string {
  const trimmed = html.trim()
  if (!trimmed || /^(<br\s*\/?>)+$/i.test(trimmed)) return ''
  return trimmed
}

function buildEmitPayloadForInput(index: number): Block[] {
  const n = props.modelValue.length
  const allowFullDomSnapshot = !virtualEnabled.value && n <= FULL_DOM_SNAPSHOT_MAX_BLOCKS
  if (allowFullDomSnapshot) {
    return props.modelValue.map((block, i) => {
      const el = blockRefs.value.get(i)
      if (!el) return { ...block }
      const html = sanitizeBlockContent(el.innerHTML || '')
      return { ...block, content: html }
    })
  }
  const newBlocks = [...props.modelValue]
  const el = blockRefs.value.get(index)
  if (!el) return newBlocks
  newBlocks[index] = { ...newBlocks[index], content: sanitizeBlockContent(el.innerHTML || '') }
  return newBlocks
}

/** 保存或离开编辑页前调用：取消防抖并从 DOM 拉齐内容，避免未刷新的防抖丢字 */
function flushPendingSync() {
  clearContentEmitTimer()
  const blocks = props.modelValue.map((block, index) => {
    const el = blockRefs.value.get(index)
    if (!el) return { ...block }
    return { ...block, content: sanitizeBlockContent(el.innerHTML || '') }
  })
  emit('update:modelValue', blocks)
}

function updateBlock(index: number) {
  if (props.previewMode) return
  const el = blockRefs.value.get(index)
  if (!el) return
  emit('content-dirty')
  scheduleContentUpdate(buildEmitPayloadForInput(index))
  debouncedSaveHistory()
}

function onBlockFocus(index: number) {
  if (focusBlurTimer) {
    clearTimeout(focusBlurTimer)
    focusBlurTimer = null
  }
  focusedIndex.value = index
  toolbarVisibleIndex.value = index
}

function handleBlur() {
  // 延迟判断，只有真正离开编辑器时才清空，避免块间切换时把新焦点误清掉
  if (focusBlurTimer) clearTimeout(focusBlurTimer)
  focusBlurTimer = setTimeout(() => {
    focusBlurTimer = null
    const ae = document.activeElement
    if (ae instanceof HTMLElement) {
      for (const el of blockRefs.value.values()) {
        if (el === ae) return
      }
    }
    focusedIndex.value = -1
  }, 150)
}

function handleEnter(index: number, event: Event) {
  if (props.previewMode) {
    event.preventDefault()
    return
  }
  const target = event.target as HTMLElement
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return

  // 检查是否是斜杠命令菜单激活状态
  if (slashMenuVisible.value) {
    event.preventDefault()
    applySlashCommand(selectedSlashIndex.value, index)
    return
  }

  const range = selection.getRangeAt(0)
  const hasHtml = /<(b|i|u|strong|em)\b/i.test(target.innerHTML || '')
  let beforeContent: string
  let afterContent: string
  if (hasHtml) {
    const beforeRange = document.createRange()
    beforeRange.setStart(target, 0)
    beforeRange.setEnd(range.startContainer, range.startOffset)
    const afterRange = document.createRange()
    afterRange.setStart(range.endContainer, range.endOffset)
    afterRange.setEnd(target, target.childNodes.length)
    beforeContent = sanitizeBlockContent(rangeToHtml(beforeRange))
    afterContent = sanitizeBlockContent(rangeToHtml(afterRange))
  } else {
    const text = target.textContent || ''
    const cursorPosition = getCursorPosition(target)
    beforeContent = text.slice(0, cursorPosition)
    afterContent = text.slice(cursorPosition)
  }
  const newBlocks = [...props.modelValue]
  newBlocks[index] = { ...newBlocks[index], content: beforeContent }
  const newBlock: Block = {
    id: generateId(),
    type: 'paragraph',
    content: afterContent,
    props: {}
  }
  newBlocks.splice(index + 1, 0, newBlock)
  emitContentUpdateNow(newBlocks)
  saveHistory()
  nextTick(() => {
    const ni = index + 1
    let el = blockRefs.value.get(ni)
    nextTick(() => {
      el = blockRefs.value.get(ni)
      if (el) {
        el.focus({ preventScroll: true })
        setCursorToStart(el)
      }
    })
  })
}

// 滚动元素到可视区域，但避免跳转到页面底部
function scrollElementIntoView(element: HTMLElement) {
  // 禁用编辑器自动滚动：避免光标/段落类型切换导致视口跳动。
  // 让浏览器/用户手动滚动保持可控；我们在 focus 时通常使用 preventScroll=true。
  void element
}

function rangeToHtml(range: Range): string {
  const fragment = range.cloneContents()
  const div = document.createElement('div')
  div.appendChild(fragment)
  return div.innerHTML
}

function handleBackspace(index: number, event: Event) {
  if (props.previewMode) {
    event.preventDefault()
    return
  }
  const target = event.target as HTMLElement
  const text = target.textContent || ''
  const cursorPosition = getCursorPosition(target)
  const currentBlock = props.modelValue[index]

  // 如果在斜杠命令菜单中，隐藏菜单
  if (slashMenuVisible.value) {
    hideSlashMenu()
  }

  // 图片块：段首退格不与上一块合并（避免丢失插图）；空说明则删除整块
  if (currentBlock?.type === 'image' && index > 0 && cursorPosition === 0) {
    event.preventDefault()
    if (text === '') {
      const newBlocks = props.modelValue.filter((_, i) => i !== index)
      emitContentUpdateNow(newBlocks)
      saveHistory()
      nextTick(() => {
        const el = blockRefs.value.get(index - 1)
        if (el) {
          el.focus({ preventScroll: true })
          setCursorToEnd(el)
        }
      })
    } else {
      const el = blockRefs.value.get(index - 1)
      if (el) {
        el.focus({ preventScroll: true })
        setCursorToEnd(el)
      }
    }
    return
  }

  // 在块的最开始位置按 Backspace，且不是第一个块
  if (index > 0 && cursorPosition === 0) {
    event.preventDefault()

    const prevBlock = props.modelValue[index - 1]

    // 将当前块内容合并到上一个块
    const newContent = prevBlock.content + currentBlock.content
    const newBlocks = [...props.modelValue]
    newBlocks[index - 1] = { ...prevBlock, content: newContent }
    newBlocks.splice(index, 1)

    emitContentUpdateNow(newBlocks)
    saveHistory()

    nextTick(() => {
      const el = blockRefs.value.get(index - 1)
      if (el) {
        el.focus({ preventScroll: true })
        // 将光标移到合并前的位置（即上一个块原来的末尾）
        setCursorToPosition(el, prevBlock.content.length)
      }
    })
    return
  }

  // 空块删除（原有逻辑）
  if (text === '' && props.modelValue.length > 1) {
    event.preventDefault()
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emitContentUpdateNow(newBlocks)
    saveHistory()

    nextTick(() => {
      const prevIndex = index - 1
      const el = blockRefs.value.get(prevIndex)
      if (el) {
        el.focus({ preventScroll: true })
        scrollElementIntoView(el)
        // 将光标移到末尾
        setCursorToEnd(el)
      }
    })
  }
}

function moveFocus(index: number, direction: number, event: Event) {
  const ke = event as KeyboardEvent
  if (ke.ctrlKey || ke.metaKey || ke.altKey || ke.shiftKey) {
    return
  }
  const newIndex = index + direction
  if (newIndex >= 0 && newIndex < props.modelValue.length) {
    event.preventDefault()
    if (virtualEnabled.value && !blockRefs.value.get(newIndex)) {
      scrollToBlockIndex(newIndex, 'nearest', 'auto', true)
    }
    nextTick(() => {
      const el = blockRefs.value.get(newIndex)
      if (el) {
        el.focus({ preventScroll: true })
        scrollElementIntoView(el)
      }
    })
  }
}

function handleKeydown(index: number, event: KeyboardEvent) {
  if (props.previewMode) {
    if (slashMenuVisible.value) {
      hideSlashMenu()
      event.preventDefault()
      return
    }
    if (event.key === 'Escape') {
      clearBlockSelection()
      return
    }
    const isMod = event.ctrlKey || event.metaKey
    const key = event.key.toLowerCase()
    if (isMod && (key === 's' || key === 'p' || key === 'r')) {
      return
    }
    if (isMod && event.shiftKey && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
      event.preventDefault()
      tryMoveBlocks(event.key === 'ArrowUp' ? -1 : 1, index)
      return
    }
    if (isMod && key === 'z' && !event.shiftKey) {
      event.preventDefault()
      undo()
      return
    }
    if (isMod && (key === 'y' || (key === 'z' && event.shiftKey))) {
      event.preventDefault()
      redo()
      return
    }
    if (isMod && key === 'd' && event.shiftKey) {
      event.preventDefault()
      if (props.modelValue.length > 1) handleCommand('delete', index)
      return
    }
    if (isMod && key === 'a') {
      event.preventDefault()
      selectAllBlocks()
      return
    }
    if (isMod && key === 'v') {
      event.preventDefault()
      return
    }
    if (selectedBlocks.value.size > 0 && isMod) {
      if (key === 'c') {
        event.preventDefault()
        copySelectedBlocks()
        return
      }
      if (key === 'x') {
        event.preventDefault()
        cutSelectedBlocks()
        return
      }
      if (key === 'delete' || key === 'backspace') {
        event.preventDefault()
        deleteSelectedBlocks()
        return
      }
    }
    if (isMod && ['1', '2', '3', '4', '5', '6', '0', 'b', 'i', 'u', 'f'].includes(key)) {
      event.preventDefault()
      return
    }
    if (!isMod) {
      if (event.key === 'Tab') return
      if (event.key === 'ArrowUp' || event.key === 'ArrowDown') return
      const k = event.key
      if (k === 'Enter' || k === 'Backspace' || k === 'Delete' || k.length === 1) {
        event.preventDefault()
      }
      return
    }
    return
  }

  // 斜杠命令菜单导航
  if (slashMenuVisible.value) {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault()
        selectedSlashIndex.value = (selectedSlashIndex.value + 1) % filteredSlashCommands.value.length
        return
      case 'ArrowUp':
        event.preventDefault()
        selectedSlashIndex.value = (selectedSlashIndex.value - 1 + filteredSlashCommands.value.length) % filteredSlashCommands.value.length
        return
      case 'Enter':
        event.preventDefault()
        applySlashCommand(selectedSlashIndex.value, index)
        return
      case 'Escape':
        event.preventDefault()
        hideSlashMenu()
        return
      case 'Backspace':
        // 更新斜杠查询
        if (slashQuery.value.length > 0) {
          slashQuery.value = slashQuery.value.slice(0, -1)
          selectedSlashIndex.value = 0
        } else {
          hideSlashMenu()
        }
        return
      default:
        // 累积查询字符
        if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
          slashQuery.value += event.key
          selectedSlashIndex.value = 0
          return
        }
        break
    }
  }

  // 检测斜杠命令触发
  if (event.key === '/' && !event.ctrlKey && !event.metaKey) {
    const el = blockRefs.value.get(index)
    if (el) {
      const text = el.textContent || ''
      const selection = window.getSelection()
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        const cursorPos = getCursorPosition(el)
        // 只有在开头或空格后才触发斜杠命令
        if (cursorPos === 0 || text[cursorPos - 1] === ' ' || text[cursorPos - 1] === '\n') {
          const rect = range.getBoundingClientRect()
          showSlashMenu(index, rect)
        }
      }
    }
    return
  }

  // Esc 清除多选
  if (event.key === 'Escape') {
    clearBlockSelection()
    return
  }

  const isMod = event.ctrlKey || event.metaKey
  if (!isMod) return
  const key = event.key.toLowerCase()

  // Ctrl/Cmd+Shift+↑↓ 移动块（单块或连续多选整体）
  if (event.shiftKey && (event.key === 'ArrowUp' || event.key === 'ArrowDown')) {
    event.preventDefault()
    const delta = event.key === 'ArrowUp' ? -1 : 1
    tryMoveBlocks(delta, index)
    return
  }

  // 撤销 Ctrl+Z
  if (key === 'z' && !event.shiftKey) {
    event.preventDefault()
    undo()
    return
  }

  // 重做 Ctrl+Y 或 Ctrl+Shift+Z
  if (key === 'y' || (key === 'z' && event.shiftKey)) {
    event.preventDefault()
    redo()
    return
  }

  // 全选所有块
  if (key === 'a') {
    event.preventDefault()
    selectAllBlocks()
    return
  }

  if (key === '1') {
    event.preventDefault()
    handleCommand('heading', index)
    return
  }
  if (key === '2') {
    event.preventDefault()
    handleCommand('subheading', index)
    return
  }
  if (key === '3') {
    event.preventDefault()
    handleCommand('quote', index)
    return
  }
  if (key === '4') {
    event.preventDefault()
    handleCommand('list', index)
    return
  }
  if (key === '5') {
    event.preventDefault()
    handleCommand('code', index)
    return
  }
  if (key === '6') {
    event.preventDefault()
    handleCommand('divider', index)
    return
  }
  if (key === '0') {
    event.preventDefault()
    handleCommand('paragraph', index)
    return
  }
  if (key === 'd' && event.shiftKey) {
    event.preventDefault()
    if (props.modelValue.length > 1) handleCommand('delete', index)
    return
  }

  // 多选块操作：复制、粘贴、删除
  if (selectedBlocks.value.size > 0) {
    // 复制选中的块
    if (key === 'c') {
      event.preventDefault()
      copySelectedBlocks()
      return
    }
    // 剪切选中的块
    if (key === 'x') {
      event.preventDefault()
      cutSelectedBlocks()
      return
    }
    // 删除选中的块
    if (key === 'delete' || key === 'backspace') {
      event.preventDefault()
      deleteSelectedBlocks()
      return
    }
  }

  // 粘贴块
  if (key === 'v') {
    const pasted = pasteBlocks(index)
    if (pasted) {
      event.preventDefault()
      return
    }
  }

  if (key === 'b') {
    event.preventDefault()
    applyFormat(index, 'bold')
    return
  }
  if (key === 'i') {
    event.preventDefault()
    applyFormat(index, 'italic')
    return
  }
  if (key === 'u') {
    event.preventDefault()
    applyFormat(index, 'underline')
    return
  }
  // 专注模式快捷键
  if (key === 'f') {
    event.preventDefault()
    toggleFocusMode()
    return
  }
}

// ========== 多选块操作：复制、剪切、删除 ==========
const copiedBlocks = ref<Block[]>([])

function copySelectedBlocks() {
  if (selectedBlocks.value.size === 0) return

  const sortedIndices = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  copiedBlocks.value = sortedIndices.map(i => ({ ...props.modelValue[i], id: generateId() }))

  // 也复制到系统剪贴板
  const textContent = sortedIndices.map(i => stripHtml(props.modelValue[i].content)).join('\n\n')
  navigator.clipboard.writeText(textContent).catch(() => {
    // 忽略剪贴板权限错误
  })

  ElMessage.success(`已复制 ${copiedBlocks.value.length} 个块`)
  clearBlockSelection()
}

function cutSelectedBlocks() {
  if (selectedBlocks.value.size === 0) return

  copySelectedBlocks()
  deleteSelectedBlocks()
}

function deleteSelectedBlocks() {
  if (selectedBlocks.value.size === 0) return

  const selectedSet = new Set(selectedBlocks.value)
  let newBlocks = props.modelValue.filter((_, i) => !selectedSet.has(i))

  // 确保至少保留一个块
  if (newBlocks.length === 0) {
    newBlocks = [{
      id: generateId(),
      type: 'paragraph',
      content: '',
      props: {}
    }]
  }

  emitContentUpdateNow(newBlocks)
  saveHistory()
  clearBlockSelection()
  ElMessage.success('已删除选中的块')
}

function onMultiBatchStyleCommand(cmd: string) {
  if (!cmd || cmd.startsWith('__')) return
  if (selectedBlocks.value.size === 0) return
  if (props.previewMode) {
    if (cmd === 'move:up') tryMoveBlocks(-1, multiToolbarAnchorIndex.value)
    else if (cmd === 'move:down') tryMoveBlocks(1, multiToolbarAnchorIndex.value)
    return
  }

  if (cmd.startsWith('type:')) {
    const t = cmd.slice(5) as Block['type']
    batchSetBlockType(t)
    return
  }
  if (cmd.startsWith('fmt:')) {
    const f = cmd.slice(4) as 'bold' | 'italic' | 'underline'
    batchApplyFormat(f)
    return
  }
  if (cmd === 'move:up') {
    tryMoveBlocks(-1, multiToolbarAnchorIndex.value)
    return
  }
  if (cmd === 'move:down') {
    tryMoveBlocks(1, multiToolbarAnchorIndex.value)
  }
}

function batchSetBlockType(type: Block['type']) {
  if (type === 'image') return
  const indices = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  if (indices.length === 0) return

  const newBlocks = [...props.modelValue]
  for (const i of indices) {
    const prev = newBlocks[i]
    if (!prev) continue
    let next: Block = { ...prev, type }
    if (prev.type === 'image') {
      next = { ...next, props: {} }
    }
    newBlocks[i] = next
  }

  emitContentUpdateNow(newBlocks)
  saveHistory()
  nextTick(() => initBlockContents())
  ElMessage.success(`已更新 ${indices.length} 个块的文体`)
}

function wrapEntireRichText(html: string, cmd: 'bold' | 'italic' | 'underline'): string {
  const tag = cmd === 'bold' ? 'b' : cmd === 'italic' ? 'i' : 'u'
  const trimmed = html.trim()
  if (!trimmed) return html
  const re = new RegExp(`^<${tag}\\b[^>]*>[\\s\\S]*</${tag}>$`, 'i')
  if (re.test(trimmed)) return html
  return `<${tag}>${trimmed}</${tag}>`
}

function batchApplyFormat(cmd: 'bold' | 'italic' | 'underline') {
  const indices = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  if (indices.length === 0) return

  const newBlocks = props.modelValue.map((b) => ({ ...b }))

  for (const i of indices) {
    const el = blockRefs.value.get(i)
    if (el) {
      el.focus()
      const sel = window.getSelection()
      if (sel) {
        const range = document.createRange()
        range.selectNodeContents(el)
        sel.removeAllRanges()
        sel.addRange(range)
        document.execCommand(cmd, false)
      }
      newBlocks[i] = { ...newBlocks[i], content: sanitizeBlockContent(el.innerHTML || '') }
    } else {
      const prev = newBlocks[i].content || ''
      if (!sanitizeBlockContent(prev)) continue
      newBlocks[i] = { ...newBlocks[i], content: wrapEntireRichText(prev, cmd) }
    }
  }

  emitContentUpdateNow(newBlocks)
  saveHistory()
  nextTick(() => initBlockContents())
  ElMessage.success(`已为 ${indices.length} 个块应用${cmd === 'bold' ? '加粗' : cmd === 'italic' ? '斜体' : '下划线'}`)
}

function pasteBlocks(afterIndex: number): boolean {
  if (copiedBlocks.value.length === 0) return false

  const newBlocks = [...props.modelValue]
  const blocksToInsert = copiedBlocks.value.map(b => ({ ...b, id: generateId() }))

  newBlocks.splice(afterIndex + 1, 0, ...blocksToInsert)
  emitContentUpdateNow(newBlocks)
  saveHistory()

  nextTick(() => {
    const focusIndex = afterIndex + blocksToInsert.length
    const el = blockRefs.value.get(focusIndex)
    if (el) {
      el.focus({ preventScroll: true })
    }
  })

  ElMessage.success(`已粘贴 ${blocksToInsert.length} 个块`)
  return true
}

function emitPolish(index: number) {
  const block = props.modelValue[index]
  if (!block) return

  // 多选状态下：如果当前块在选中集合中，则对“全部选中块”执行润色
  if (selectedBlocks.value.size > 1 && selectedBlocks.value.has(index)) {
    emitPolishSelected()
    return
  }

  const text = block?.content ? stripHtml(block.content) : ''
  if (!text.trim()) {
    ElMessage.warning('请先输入要润色的内容')
    return
  }
  emit('polish', { index, text })
}

function emitPolishSelected() {
  emitRewriteSelected('polish')
}

function emitReviseSelected() {
  emitRewriteSelected('revise')
}

function emitExpandSelected() {
  emitRewriteSelected('expand')
}

/** 仅根据多选块中的文字生成插图（跳过插图块） */
function emitGenerateImageForSelection() {
  const indices = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  if (indices.length === 0) return

  const parts: string[] = []
  for (const i of indices) {
    const b = props.modelValue[i]
    if (!b || b.type === 'image') continue
    const c = b.content ? stripHtml(b.content).trim() : ''
    if (c) parts.push(c)
  }
  const text = parts.join('\n\n')
  if (!text.trim()) {
    ElMessage.warning('选中的块没有可用文字（插图块已跳过）')
    return
  }

  clearBlockSelection()
  emit('generate-image-for-selection', { indices, text })
}

function emitRewriteSelected(action: 'polish' | 'revise' | 'expand') {
  const indices = Array.from(selectedBlocks.value).sort((a, b) => a - b)
  if (indices.length === 0) return

  const parts = indices
    .map(i => {
      const b = props.modelValue[i]
      return b?.content ? stripHtml(b.content) : ''
    })
    .filter(t => t.trim())

  const text = parts.join('\n\n')
  if (!text.trim()) {
    const msg = action === 'polish'
      ? '请先输入要润色的内容'
      : action === 'revise'
        ? '请先输入要修改的内容'
        : '请先输入要扩展的内容'
    ElMessage.warning(msg)
    return
  }

  // 启动 AI 前清空选择，避免替换后下标变化导致高亮错位
  clearBlockSelection()

  if (action === 'polish') {
    emit('polish-selected', { indices, text })
  } else if (action === 'revise') {
    emit('revise-selected', { indices, text })
  } else {
    emit('expand-selected', { indices, text })
  }
}

function stripHtml(html: string): string {
  const div = document.createElement('div')
  div.innerHTML = html
  return div.textContent || ''
}

function plainTextToHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text ?? ''
  return div.innerHTML.replace(/\n/g, '<br>')
}

const previewEditDialogVisible = ref(false)
const previewEditDialogIndex = ref<number | null>(null)
const previewEditDialogText = ref('')

function openPreviewTextEdit(index: number) {
  if (!props.previewMode) return
  if (index < 0 || index >= props.modelValue.length) return
  previewEditDialogIndex.value = index
  previewEditDialogText.value = stripHtml(props.modelValue[index]?.content || '')
  previewEditDialogVisible.value = true
}

function applyPreviewTextEdit() {
  const idx = previewEditDialogIndex.value
  if (idx == null || idx < 0 || idx >= props.modelValue.length) {
    previewEditDialogVisible.value = false
    return
  }
  const prev = props.modelValue[idx]
  if (!prev) {
    previewEditDialogVisible.value = false
    return
  }
  const newBlocks = [...props.modelValue]
  const nextHtml = sanitizeBlockContent(plainTextToHtml(previewEditDialogText.value || ''))
  newBlocks[idx] = { ...prev, content: nextHtml }
  emitContentUpdateNow(newBlocks)
  saveHistory()
  nextTick(() => initBlockContents())
  previewEditDialogVisible.value = false
}

function applyFormat(index: number, command: 'bold' | 'italic' | 'underline') {
  if (props.previewMode) return
  const el = blockRefs.value.get(index)
  if (!el) return
  el.focus()
  document.execCommand(command, false)
  updateBlock(index)
}

function isFormatActive(index: number, command: 'bold' | 'italic' | 'underline'): boolean {
  const el = blockRefs.value.get(index)
  if (!el || document.activeElement !== el) return false
  return document.queryCommandState(command)
}

function handleCommand(command: string, index: number) {
  if (props.previewMode) {
    const allowed = command === 'moveUp' || command === 'moveDown' || command === 'delete'
    if (!allowed) return
  }
  if (command === 'moveUp') {
    tryMoveBlocks(-1, index)
    return
  }
  if (command === 'moveDown') {
    tryMoveBlocks(1, index)
    return
  }
  if (command === 'delete') {
    if (props.modelValue.length <= 1) return
    const newBlocks = props.modelValue.filter((_, i) => i !== index)
    emitContentUpdateNow(newBlocks)
    saveHistory()
  } else {
    const newBlocks = [...props.modelValue]
    const prev = newBlocks[index]
    let next: Block = { ...prev, type: command as Block['type'] }
    if (prev.type === 'image' && command !== 'image') {
      next = { ...next, props: {} }
    }
    newBlocks[index] = next
    emitContentUpdateNow(newBlocks)
    saveHistory()

    // 保持焦点
    nextTick(() => {
      const el = blockRefs.value.get(index)
      if (el) {
        el.focus({ preventScroll: true })
        scrollElementIntoView(el)
      }
    })
  }
}

function handleEditorClick(event: Event) {
  // 如果点击的是编辑器空白区域，添加新块
  const target = event.target as HTMLElement
  if (target.classList.contains('block-editor') && !props.modelValue.length) {
    addBlock(-1)
  }
  // 点击编辑器空白区域时清除选择
  if (target.classList.contains('block-editor')) {
    clearBlockSelection()
  }
}

function handleBlockMouseDown(index: number, event: MouseEvent) {
  // 如果正在多选模式或按住修饰键
  if (isMultiSelectMode.value || event.ctrlKey || event.metaKey || event.shiftKey) {
    event.preventDefault()
    toggleBlockSelection(index, event)
  }
}

function getCursorPosition(element: HTMLElement): number {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return 0
  const range = selection.getRangeAt(0)
  const preCaretRange = range.cloneRange()
  preCaretRange.selectNodeContents(element)
  preCaretRange.setEnd(range.endContainer, range.endOffset)
  return preCaretRange.toString().length
}

function setCursorToStart(element: HTMLElement) {
  const range = document.createRange()
  const selection = window.getSelection()
  range.selectNodeContents(element)
  range.collapse(true)
  selection?.removeAllRanges()
  selection?.addRange(range)
}

function setCursorToEnd(element: HTMLElement) {
  const range = document.createRange()
  const selection = window.getSelection()
  range.selectNodeContents(element)
  range.collapse(false)
  selection?.removeAllRanges()
  selection?.addRange(range)
}

function setCursorToPosition(element: HTMLElement, position: number) {
  const selection = window.getSelection()
  if (!selection) return

  const range = document.createRange()
  const textNodes = getTextNodes(element)
  let currentPos = 0

  for (const node of textNodes) {
    const nodeLength = node.textContent?.length || 0
    if (currentPos + nodeLength >= position) {
      const offset = position - currentPos
      range.setStart(node, offset)
      range.setEnd(node, offset)
      break
    }
    currentPos += nodeLength
  }

  if (textNodes.length === 0) {
    range.selectNodeContents(element)
    range.collapse(true)
  }

  selection.removeAllRanges()
  selection.addRange(range)
}

function getTextNodes(element: Node): Text[] {
  const textNodes: Text[] = []
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, null)
  let node: Node | null
  while ((node = walker.nextNode()) !== null) {
    textNodes.push(node as Text)
  }
  return textNodes
}

/**
 * 供父组件插入图片等块时定位：多选时取最大下标，否则取当前焦点块，否则文末最后一块。
 * 空文档返回 -1（在父组件 splice 到开头）。
 */
function getImageInsertAfterIndex(): number {
  const n = props.modelValue.length
  if (n === 0) return -1
  if (selectedBlocks.value.size > 0) {
    return Math.max(...Array.from(selectedBlocks.value))
  }
  if (focusedIndex.value >= 0 && focusedIndex.value < n) {
    return focusedIndex.value
  }
  return n - 1
}

function focusBlock(index: number, opts?: { cursor?: 'start' | 'end'; align?: 'start' | 'nearest'; behavior?: ScrollBehavior; focus?: boolean }) {
  const n = props.modelValue.length
  if (index < 0 || index >= n) return
  const shouldFocus = opts?.focus ?? !props.previewMode
  if (shouldFocus) {
    if (focusBlurTimer) {
      clearTimeout(focusBlurTimer)
      focusBlurTimer = null
    }
    focusedIndex.value = index
    toolbarVisibleIndex.value = index
  }
  // 虚拟滚动：确保目标块在渲染范围内
  if (virtualEnabled.value) {
    // 如果已经在视口内，不滚动
    const el = scrollEl.value
    if (el) {
      const offsets = blockOffsets.value
      if (offsets.length === n + 1) {
        const top = offsets[index]
        const h = getHeightForIndex(index)
        const st = el.scrollTop
        const vh = el.clientHeight
        const isInViewport = top >= st - 12 && top + h <= st + vh + 12
        if (!isInViewport) {
          scrollToBlockIndex(index, opts?.align ?? 'nearest', opts?.behavior ?? 'auto', true)
        }
      }
    }
  }
  nextTick(() => {
    const el = blockRefs.value.get(index)
    if (!el) return
    if (!virtualEnabled.value) {
      el.scrollIntoView({ block: opts?.align === 'start' ? 'start' : 'nearest', behavior: opts?.behavior ?? 'auto' })
    }
    if (!shouldFocus) return
    // 避免重复聚焦（如果已经是活动元素）
    if (document.activeElement === el) {
      if (opts?.cursor === 'start') setCursorToStart(el)
      else setCursorToEnd(el)
      return
    }
    el.focus({ preventScroll: true })
    if (opts?.cursor === 'start') setCursorToStart(el)
    else setCursorToEnd(el)
  })
}

defineExpose({ getImageInsertAfterIndex, flushPendingSync, focusBlock })
</script>

<style scoped lang="scss">
.block-editor {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
  transition: all 0.3s ease;
  
  &.focus-mode {
    .block-wrapper:not(.is-focused) {
      opacity: 0.3;
      filter: blur(1px);
    }
    
    .block-wrapper.is-focused {
      transform: scale(1.01);
      transition: all 0.3s ease;
    }
  }

  &.preview-mode {
    .block-content {
      cursor: default;
      user-select: text;
    }
  }
}

.block-list-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
}

.virtual-pad {
  width: 100%;
  flex-shrink: 0;
  pointer-events: none;
}

.block-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 0;
  border-radius: 8px;
  transition: all 0.2s ease;
  position: relative;
  
  &:hover {
    background: rgba(var(--coffee-primary-rgb), 0.03);
    
    .block-handle,
    .block-actions {
      opacity: 1;
    }
  }
  
  &.is-focused {
    .block-content {
      background: var(--coffee-sidebar-shadow);
    }
  }
}

.block-handle {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  color: var(--coffee-text-light);
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
  margin-top: 4px;
  
  &:hover {
    background: rgba(var(--coffee-primary-rgb), 0.1);
    color: var(--coffee-primary);
  }
}

.block-content {
  flex: 1;
  min-height: 36px;
  padding: 6px 12px;
  line-height: 1.8;
  outline: none;
  border-radius: 6px;
  transition: all 0.2s;
  color: var(--coffee-text);
  font-size: 16px;
  white-space: pre-wrap;
  word-break: break-word;
  
  &[data-type="heading"] {
    font-size: 24px;
    font-weight: 700;
    color: var(--coffee-text);
    margin: 8px 0;
    
    &:empty::before {
      content: '标题';
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="subheading"] {
    font-size: 18px;
    font-weight: 600;
    color: var(--coffee-text);
    margin: 6px 0;
    
    &:empty::before {
      content: '小标题';
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="quote"] {
    border-left: 3px solid var(--coffee-primary-light);
    padding-left: 20px;
    color: var(--coffee-text-secondary);
    font-style: italic;
    background: var(--coffee-sidebar-shadow);
    
    &:empty::before {
      content: '引用内容';
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="list"] {
    padding-left: 32px;
    position: relative;
    
    &::before {
      content: "•";
      position: absolute;
      left: 12px;
      color: var(--coffee-primary);
      font-weight: bold;
    }
    
    &:empty::before {
      content: "• 列表项";
      color: var(--coffee-text-light);
    }
  }
  
  &[data-type="code"] {
    font-family: 'Fira Code', 'Monaco', 'Consolas', monospace;
    font-size: 14px;
    background: #f5f5f5;
    padding: 16px;
    border-radius: 8px;
    white-space: pre-wrap;
    color: #333;
    
    &:empty::before {
      content: '// 代码块';
      color: var(--coffee-text-light);
      font-style: italic;
    }
  }
  
  &[data-type="divider"] {
    height: 1px;
    background: linear-gradient(to right, transparent, var(--coffee-border), transparent);
    padding: 0;
    min-height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: none;
    
    &::before {
      content: '***';
      color: var(--coffee-text-light);
      font-size: 12px;
      letter-spacing: 4px;
    }
  }
  
  &[data-type="paragraph"]:empty::before {
    content: '输入正文...';
    color: var(--coffee-text-light);
  }
  
  &:focus {
    background: var(--coffee-sidebar-shadow);
  }
}

/* 快捷操作栏：绝对定位浮动在块上方，过长时换行避免被右侧面板遮挡 */
.quick-toolbar {
  position: absolute;
  left: 32px;
  bottom: 100%;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
  max-width: min(520px, calc(100vw - 440px));
  padding: 6px 8px;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 8px;
  box-shadow: 0 4px 12px var(--coffee-shadow);
  z-index: 9999;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--coffee-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  &:hover {
    background: var(--coffee-shadow);
    color: var(--coffee-primary);
  }
  &.active {
    background: var(--coffee-shadow-hover);
    color: var(--coffee-primary);
    font-weight: 500;
  }
  &.delete:hover:not(:disabled) {
    background: rgba(245, 108, 108, 0.12);
    color: #f56c6c;
  }
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .el-icon { font-size: 16px; }
  &.ai-btn {
    color: var(--coffee-primary);
    &:hover { color: var(--coffee-primary); }
  }
  &.format-btn {
    min-width: 28px;
    padding: 6px 8px;
    font-weight: 600;
    .fmt-bold { font-weight: 700; }
    .fmt-italic { font-style: italic; font-weight: 600; }
    .fmt-underline { text-decoration: underline; font-weight: 600; }
  }
}

.toolbar-divider {
  width: 1px;
  height: 18px;
  background: var(--coffee-border);
  margin: 0 4px;
}

.toolbar-enter-active,
.toolbar-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.toolbar-enter-from,
.toolbar-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 多选块的视觉反馈 */
.block-wrapper.is-selected {
  background: rgba(var(--coffee-primary-rgb), 0.08) !important;
  border-left: 3px solid var(--coffee-primary);
}

.block-editor.multi-select .block-wrapper {
  cursor: pointer;
}

.block-editor.multi-select .block-wrapper:hover {
  background: rgba(var(--coffee-primary-rgb), 0.04);
}

/* 斜杠命令菜单 */
.slash-menu {
  position: fixed;
  z-index: 10000;
  min-width: 240px;
  max-width: 320px;
  max-height: 400px;
  overflow-y: auto;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
  padding: 8px 0;
}

.slash-menu-header {
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.slash-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  margin: 0 6px;
  border-radius: 6px;
}

.slash-menu-item:hover,
.slash-menu-item.active {
  background: var(--coffee-shadow);
}

.slash-menu-item.active {
  background: rgba(var(--coffee-primary-rgb), 0.12);
}

.slash-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  color: var(--coffee-primary);
  font-size: 18px;
}

.slash-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.slash-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--coffee-text);
}

.slash-shortcut {
  font-size: 12px;
  color: var(--coffee-text-light);
}

.slash-menu-enter-active,
.slash-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.slash-menu-enter-from,
.slash-menu-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(-8px);
}

.block-actions {
  opacity: 0;
  display: flex;
  align-items: center;
  flex-shrink: 0;
  margin-top: 4px;
}

.action-icon {
  padding: 6px;
  cursor: pointer;
  color: var(--coffee-text-light);
  border-radius: 4px;
  transition: all 0.2s;
  
  &:hover {
    color: var(--coffee-primary);
    background: var(--coffee-shadow);
  }
}

.empty-state {
  flex: 1;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 20px;
  color: var(--coffee-text-light);
  cursor: pointer;
  border-radius: 16px;
  border: 2px dashed var(--coffee-border);
  transition: all 0.3s;
  
  &:hover {
    border-color: var(--coffee-primary-light);
    background: rgba(var(--coffee-primary-rgb), 0.02);
    color: var(--coffee-primary);
  }
  
  .empty-icon {
    width: 64px;
    height: 64px;
    background: linear-gradient(135deg, var(--coffee-bg-warm) 0%, var(--coffee-divider) 100%);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    
    .el-icon {
      font-size: 28px;
      color: var(--coffee-primary-light);
    }
  }
  
  span {
    font-size: 15px;
  }
  .shortcut-hint {
    font-size: 12px;
    opacity: 0.7;
    white-space: nowrap;
    display: block;
  }
}

:deep(.delete-item) {
  color: #f56c6c;
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  white-space: nowrap;
  gap: 16px;
}

:deep(.shortcut) {
  margin-left: auto;
  padding-left: 12px;
  font-size: 12px;
  color: var(--coffee-text-light);
  flex-shrink: 0;
  white-space: nowrap;
}

/* 右键快捷菜单 */
.context-menu {
  position: fixed;
  z-index: 10000;
  min-width: 200px;
  max-width: 280px;
  max-height: 70vh;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 6px 0;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
}

.context-menu-section {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.context-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 14px;
  border: none;
  background: transparent;
  color: var(--coffee-text-secondary);
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  border-radius: 6px;
  margin: 0 4px;
  width: calc(100% - 8px);
  box-sizing: border-box;
}
.context-item .el-icon {
  font-size: 16px;
  flex-shrink: 0;
}
.context-item .shortcut {
  margin-left: auto;
  font-size: 11px;
  color: var(--coffee-text-light);
}
.context-item:hover:not(:disabled) {
  background: var(--coffee-shadow);
  color: var(--coffee-primary);
}
.context-item.active {
  background: rgba(var(--coffee-primary-rgb), 0.12);
  color: var(--coffee-primary);
  font-weight: 500;
}
.context-item.ai-item {
  color: var(--coffee-primary);
}
.context-item.ai-item:hover:not(:disabled) {
  color: var(--coffee-primary);
}
.context-item.danger:hover:not(:disabled) {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}
.context-item:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.context-item .fmt-bold { font-weight: 700; }
.context-item .fmt-italic { font-style: italic; font-weight: 600; }
.context-item .fmt-underline { text-decoration: underline; font-weight: 600; }

.context-menu-divider {
  height: 1px;
  background: var(--coffee-border);
  margin: 4px 0;
}

.context-menu-enter-active,
.context-menu-leave-active {
  transition: opacity 0.12s ease, transform 0.12s ease;
}
.context-menu-enter-from,
.context-menu-leave-to {
  opacity: 0;
  transform: scale(0.96);
}

/* 多选块的视觉反馈 */
.block-wrapper.is-selected {
  background: rgba(var(--coffee-primary-rgb), 0.08) !important;
  border-left: 3px solid var(--coffee-primary);
}

.block-editor.multi-select .block-wrapper {
  cursor: pointer;
}

.block-editor.multi-select .block-wrapper:hover {
  background: rgba(var(--coffee-primary-rgb), 0.04);
}

/* 斜杠命令菜单 */
.slash-menu {
  position: fixed;
  z-index: 10000;
  min-width: 240px;
  max-width: 320px;
  max-height: 400px;
  overflow-y: auto;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 10px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
  padding: 8px 0;
}

.slash-menu-header {
  padding: 8px 16px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coffee-text-light);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.slash-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  margin: 0 6px;
  border-radius: 6px;
}

.slash-menu-item:hover,
.slash-menu-item.active {
  background: var(--coffee-shadow);
}

.slash-menu-item.active {
  background: rgba(var(--coffee-primary-rgb), 0.12);
}

.slash-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  color: var(--coffee-primary);
  font-size: 18px;
}

.slash-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.slash-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--coffee-text);
}

.slash-shortcut {
  font-size: 12px;
  color: var(--coffee-text-light);
}

.slash-menu-enter-active,
.slash-menu-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.slash-menu-enter-from,
.slash-menu-leave-to {
  opacity: 0;
  transform: scale(0.96) translateY(-8px);
}

/* 多选块工具栏 */
.multi-select-toolbar {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: var(--coffee-bg-card);
  border: 1px solid var(--coffee-border);
  border-radius: 12px;
  box-shadow: 0 8px 24px var(--coffee-shadow);
  z-index: 10001;
}

.selected-count {
  font-size: 13px;
  color: var(--coffee-text-secondary);
  margin-right: 8px;
  padding-right: 12px;
  border-right: 1px solid var(--coffee-border);
  white-space: nowrap;
}

.multi-select-toolbar .toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--coffee-text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.multi-select-toolbar .toolbar-btn:hover {
  background: var(--coffee-shadow);
  color: var(--coffee-primary);
}

.multi-select-toolbar .toolbar-btn.delete:hover {
  background: rgba(245, 108, 108, 0.12);
  color: #f56c6c;
}

.multi-batch-style-dropdown {
  display: inline-flex;
}

.multi-select-toolbar .toolbar-btn-dropdown .batch-dd-caret {
  font-size: 11px;
  margin-left: 2px;
  opacity: 0.75;
}

.multi-select-toolbar .toolbar-btn .el-icon {
  font-size: 16px;
}

.multi-select-toolbar-enter-active,
.multi-select-toolbar-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.multi-select-toolbar-enter-from,
.multi-select-toolbar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

/* 插图块 */
.block-image-section {
  margin: 8px 0 12px;
  text-align: center;
}
.block-image-el {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}
.block-image-placeholder {
  padding: 24px;
  color: var(--coffee-text-light);
  background: var(--coffee-bg-warm);
  border-radius: 8px;
  border: 1px dashed var(--coffee-border);
}
.block-type-image-caption {
  min-height: 1.5em;
}
</style>

<style lang="scss">
/* 下拉挂在 body，需非 scoped */
.multi-batch-style-popper.el-popper {
  .batch-menu-section-title {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    cursor: default;
    background: transparent !important;
  }
  .batch-menu-section-title:hover {
    background: transparent !important;
    color: var(--el-text-color-secondary);
  }
}
</style>
