<template>
  <div class="app-container">
    <el-form ref="form" :model="form" :rules="rules" label-width="120px">
      <el-form-item label="题目顺序" prop="order">
        <el-input
          v-model.number="form.order"
          type="number"
          style="width: 120px"
        />
      </el-form-item>
      <el-form-item label="题目描述" prop="content">
        <div class="markdown-editor-container">
          <div class="editor-tabs">
            <el-button
              :class="['tab-btn', { active: editorMode === 'edit' }]"
              size="small"
              @click="editorMode = 'edit'"
            >
              编辑
            </el-button>
            <el-button
              :class="['tab-btn', { active: editorMode === 'preview' }]"
              size="small"
              @click="editorMode = 'preview'"
            >
              预览
            </el-button>
          </div>

          <div v-if="editorMode === 'edit'" class="editor-content">
            <el-input
              v-model="form.content"
              type="textarea"
              :autosize="{ minRows: 8, maxRows: 20 }"
              placeholder="请输入题目描述，支持Markdown语法：

# 标题1
## 标题2
**粗体文本**
*斜体文本*
`代码`
- 列表项1
- 列表项2

支持表格：
| 列1 | 列2 |
|-----|-----|
| 内容1 | 内容2 |"
            />
          </div>

          <div v-if="editorMode === 'preview'" class="preview-content">
            <div class="markdown-preview" v-html="renderedContent" />
          </div>
        </div>
      </el-form-item>
      <el-form-item label="注意事项">
        <div class="markdown-editor-container">
          <div class="editor-tabs">
            <el-button
              :class="['tab-btn', { active: noticeEditorMode === 'edit' }]"
              size="small"
              @click="noticeEditorMode = 'edit'"
            >
              编辑
            </el-button>
            <el-button
              :class="['tab-btn', { active: noticeEditorMode === 'preview' }]"
              size="small"
              @click="noticeEditorMode = 'preview'"
            >
              预览
            </el-button>
          </div>

          <div v-if="noticeEditorMode === 'edit'" class="editor-content">
            <el-input
              v-model="form.file_description"
              type="textarea"
              :autosize="{ minRows: 4, maxRows: 12 }"
              placeholder="请输入注意事项，支持Markdown语法：

# 标题1
## 标题2
**粗体文本**
*斜体文本*
`代码`
- 列表项1
- 列表项2

支持表格：
| 列1 | 列2 |
|-----|-----|
| 内容1 | 内容2 |"
            />
          </div>

          <div v-if="noticeEditorMode === 'preview'" class="preview-content">
            <div class="markdown-preview" v-html="renderedNoticeContent" />
          </div>
        </div>
      </el-form-item>
      <el-form-item label="需要上传文件答题">
        <el-switch v-model="form.requires_file" />
      </el-form-item>

      <!-- 多文件答题设置 -->
      <el-form-item v-if="form.requires_file" label="多文件答题设置">
        <div style="margin-bottom: 16px;">
          <el-button type="primary" size="mini" @click="addRequiredFile">
            添加文件要求
          </el-button>
        </div>
        <div
          v-for="(file, idx) in form.required_files"
          :key="file.uuid"
          style="
            margin-bottom: 16px;
            border: 1px solid #eee;
            padding: 16px;
            border-radius: 4px;
          "
        >
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item :label="'文件名称'" :prop="'required_files.' + idx + '.name'">
                <el-input v-model="file.name" placeholder="请输入文件名称" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'文件类型'" :prop="'required_files.' + idx + '.type'">
                <el-select v-model="file.type" placeholder="请选择文件类型" style="width: 100%">
                  <el-option label="PDF" value="pdf" />
                  <el-option label="Word" value="doc" />
                  <el-option label="Excel" value="xls" />
                  <el-option label="图片" value="image" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'是否必填'">
                <el-switch v-model="file.required" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item :label="'文件说明'" :prop="'required_files.' + idx + '.description'">
            <el-input
              v-model="file.description"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 3 }"
              placeholder="请输入文件说明"
            />
          </el-form-item>
          <el-button
            type="danger"
            size="mini"
            style="margin-top: 8px"
            @click="removeRequiredFile(idx)"
          >
            删除文件要求
          </el-button>
        </div>
      </el-form-item>

      <!-- 资料文件设置 -->
      <el-form-item label="资料文件">
        <div style="margin-bottom: 16px;">
          <el-button type="primary" size="mini" @click="addMaterialFile">
            添加资料文件
          </el-button>
        </div>
        <div
          v-for="(file, idx) in form.material_files"
          :key="file.uuid"
          style="
            margin-bottom: 16px;
            border: 1px solid #eee;
            padding: 16px;
            border-radius: 4px;
          "
        >
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item :label="'文件名称'" :prop="'material_files.' + idx + '.name'">
                <el-input v-model="file.name" placeholder="请输入文件名称" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'文件类型'" :prop="'material_files.' + idx + '.type'">
                <el-select v-model="file.type" placeholder="请选择文件类型" style="width: 100%">
                  <el-option label="PDF" value="pdf" />
                  <el-option label="Word" value="doc" />
                  <el-option label="Excel" value="xls" />
                  <el-option label="图片" value="image" />
                  <el-option label="其他" value="other" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item :label="'上传文件'">
                <el-upload
                  :action="uploadUrl"
                  :headers="uploadHeaders"
                  :on-success="(res) => handleMaterialFileSuccess(res, idx)"
                  :on-error="handleUploadError"
                  :show-file-list="false"
                >
                  <el-button size="mini" type="primary">选择文件</el-button>
                </el-upload>
                <span v-if="file.url" style="margin-left: 8px; color: #67c23a;">
                  已上传: {{ file.originalName }}
                </span>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item :label="'文件说明'" :prop="'material_files.' + idx + '.description'">
            <el-input
              v-model="file.description"
              type="textarea"
              :autosize="{ minRows: 1, maxRows: 3 }"
              placeholder="请输入文件说明"
            />
          </el-form-item>
          <el-button
            type="danger"
            size="mini"
            style="margin-top: 8px"
            @click="removeMaterialFile(idx)"
          >
            删除资料文件
          </el-button>
        </div>
      </el-form-item>
      <el-form-item label="子问题列表">
        <div
          v-for="(sub, idx) in form.sub_questions"
          :key="sub.uuid"
          style="
            margin-bottom: 24px;
            border: 1px solid #eee;
            padding: 16px;
            border-radius: 4px;
          "
        >
          <el-row :gutter="16">
            <el-col :span="6">
              <el-form-item
                :label="'顺序'"
                :prop="'sub_questions.' + idx + '.order'"
              >
                <el-input
                  v-model.number="sub.order"
                  type="number"
                  style="width: 80px"
                />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item
                :label="'内容'"
                :prop="'sub_questions.' + idx + '.content'"
              >
                <el-input
                  v-model="sub.content"
                  type="textarea"
                  :autosize="{ minRows: 1, maxRows: 3 }"
                />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item
                :label="'类型'"
                :prop="'sub_questions.' + idx + '.question_type'"
              >
                <el-select
                  v-model="sub.question_type"
                  placeholder="请选择类型"
                  style="width: 120px"
                >
                  <el-option label="单选题" value="single_choice" />
                  <el-option label="多选题" value="multiple_choice" />
                  <el-option label="填空题" value="text" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="6">
              <el-form-item
                :label="'分值'"
                :prop="'sub_questions.' + idx + '.score'"
              >
                <el-input
                  v-model.number="sub.score"
                  type="number"
                  style="width: 80px"
                />
              </el-form-item>
            </el-col>
            <el-col :span="18">
              <div
                v-if="
                  sub.question_type === 'single_choice' ||
                    sub.question_type === 'multiple_choice'
                "
              >
                <el-form-item label="选项">
                  <div
                    v-for="(opt, oidx) in sub.options"
                    :key="opt.uuid"
                    style="
                      display: flex;
                      align-items: center;
                      margin-bottom: 5px;
                    "
                  >
                    <el-input
                      v-model="opt.content"
                      placeholder="选项内容"
                      style="width: 200px"
                    />
                    <el-checkbox
                      v-model="opt.is_correct"
                      style="margin-left: 10px"
                    >正确</el-checkbox>
                    <el-button
                      type="text"
                      @click="removeOption(idx, oidx)"
                    >删除</el-button>
                  </div>
                  <el-button
                    type="primary"
                    size="mini"
                    @click="addOption(idx)"
                  >添加选项</el-button>
                </el-form-item>
              </div>
            </el-col>
          </el-row>
          <el-button
            type="danger"
            size="mini"
            style="margin-top: 8px"
            @click="removeSubQuestion(idx)"
          >删除子问题</el-button>
        </div>
        <el-button type="primary" @click="addSubQuestion">添加子问题</el-button>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onSubmit">保存</el-button>
        <el-button @click="$router.back()">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import {
  fetchExamQuestion,
  createExamQuestion,
  updateExamQuestion
} from '@/api/exam'
function uuid() {
  return '_' + Math.random().toString(36).substr(2, 9)
}
export default {
  data() {
    return {
      form: {
        order: 1,
        content: '',
        exam_id: '',
        uuid: uuid(),
        requires_file: false,
        file_description: '',
        sub_questions: [],
        required_files: [], // 多文件答题要求
        material_files: [] // 资料文件
      },
      rules: {
        content: [
          { required: true, message: '请输入题目内容', trigger: 'blur' }
        ]
      },
      exam_id: null,
      question_id: null,
      uploadUrl: '/api/exam/upload-file',
      uploadHeaders: {
        Authorization: localStorage.getItem('token') || ''
      },
      editorMode: 'edit', // 题目描述编辑器模式：edit 或 preview
      noticeEditorMode: 'edit' // 注意事项编辑器模式：edit 或 preview
    }
  },
  computed: {
    // Markdown渲染函数 - 题目描述
    renderedContent() {
      if (!this.form.content) return ''

      return this.renderMarkdown(this.form.content)
    },
    // Markdown渲染函数 - 注意事项
    renderedNoticeContent() {
      if (!this.form.file_description) return ''

      return this.renderMarkdown(this.form.file_description)
    }
  },
  created() {
    this.exam_id = this.$route.params.exam_id
    this.form.exam_id = this.exam_id
    this.question_id = this.$route.params.question_id
    if (this.question_id) {
      fetchExamQuestion(this.exam_id, this.question_id).then((res) => {
        const data = res.data || res
        const parsedData = JSON.parse(data.sub_questions_str)

        // 2. 验证解析结果是否为数组
        if (!Array.isArray(parsedData)) {
          this.form = {
            ...data,
            required_files: data.required_files ? JSON.parse(data.required_files) : [],
            material_files: data.material_files ? JSON.parse(data.material_files) : []
          }
        } else {
          this.form = {
            ...data,
            sub_questions: parsedData,
            required_files: data.required_files ? JSON.parse(data.required_files) : [],
            material_files: data.material_files ? JSON.parse(data.material_files) : []
          }
        }
      })
    }
  },
  methods: {
    // Markdown渲染方法
    renderMarkdown(content) {
      if (!content) return ''

      // 先处理通用的加粗语法
      const processedContent = content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')

      // 然后处理其他格式
      return processedContent
        // 处理列表项
        .replace(/^[-*]\s*(.*)$/gim, '<div class="list-item">- $1</div>')
        // 处理普通段落
        .replace(/^([^-*].*)$/gim, '<div class="paragraph">$1</div>')
        // 清理空行
        .replace(/\n\s*\n/g, '')
        // 清理多余的div
        .replace(/<div class="paragraph"><\/div>/g, '')
    },

    addSubQuestion() {
      this.form.sub_questions.push({
        order: this.form.sub_questions.length + 1,
        content: '',
        question_type: '',
        score: 1,
        options: [],
        uuid: uuid()
      })
    },
    removeSubQuestion(idx) {
      this.form.sub_questions.splice(idx, 1)
    },
    addOption(subIdx) {
      const sub = this.form.sub_questions[subIdx]
      if (!sub.options) this.$set(sub, 'options', [])
      sub.options.push({ content: '', is_correct: false, uuid: uuid() })
    },
    removeOption(subIdx, optIdx) {
      this.form.sub_questions[subIdx].options.splice(optIdx, 1)
    },
    // 多文件答题相关方法
    addRequiredFile() {
      this.form.required_files.push({
        name: '',
        type: 'pdf',
        required: true,
        description: '',
        uuid: uuid()
      })
    },
    removeRequiredFile(idx) {
      this.form.required_files.splice(idx, 1)
    },
    // 资料文件相关方法
    addMaterialFile() {
      this.form.material_files.push({
        name: '',
        type: 'pdf',
        description: '',
        url: '',
        originalName: '',
        uuid: uuid()
      })
    },
    removeMaterialFile(idx) {
      this.form.material_files.splice(idx, 1)
    },
    handleMaterialFileSuccess(res, idx) {
      if (res.code === 20000) {
        this.form.material_files[idx].url = res.data.url
        this.form.material_files[idx].originalName = res.data.filename
        this.$message.success('文件上传成功')
      } else {
        this.$message.error('文件上传失败')
      }
    },
    handleUploadError() {
      this.$message.error('文件上传失败')
    },
    onSubmit() {
      this.$refs.form.validate((valid) => {
        if (!valid) return
        // 提交时去除uuid辅助字段
        const submitData = {
          ...this.form,
          sub_questions_str: JSON.stringify(this.form.sub_questions),
          required_files: JSON.stringify(this.form.required_files),
          material_files: JSON.stringify(this.form.material_files)
        }
        submitData.sub_questions = null
        submitData.id = null

        const action = this.question_id
          ? updateExamQuestion(this.question_id, submitData)
          : createExamQuestion(submitData)
        action.then(() => {
          this.$message.success('保存成功')
          this.$router.push({ path: `/exam/questionlist/${this.exam_id}` })
        })
      })
    }
  }
}
</script>

<style scoped>
.markdown-editor-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.editor-tabs {
  background: #f5f7fa;
  padding: 8px 12px;
  border-bottom: 1px solid #dcdfe6;
}

.tab-btn {
  margin-right: 8px;
  border: none;
  background: transparent;
  color: #606266;
  padding: 4px 12px;
  border-radius: 3px;
  cursor: pointer;
}

.tab-btn.active {
  background: #409eff;
  color: white;
}

.editor-content {
  padding: 12px;
}

.preview-content {
  padding: 16px;
  background: white;
  min-height: 200px;
}

.markdown-preview {
  line-height: 1.6;
  color: #333;
  font-size: 14px;
}

.markdown-preview .question-item {
  margin-bottom: 8px;
  display: flex;
  align-items: flex-start;
}

.markdown-preview .label {
  font-weight: bold;
  color: #333;
  min-width: 80px;
  margin-right: 8px;
}

.markdown-preview .value {
  color: #666;
  flex: 1;
}

.markdown-preview .list-item {
  margin: 4px 0 4px 20px;
  color: #666;
}

.markdown-preview .paragraph {
  margin: 8px 0;
  color: #666;
  line-height: 1.6;
}

.markdown-preview h1 {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
  margin: 0 0 16px 0;
  border-bottom: 2px solid #409eff;
  padding-bottom: 8px;
}

.markdown-preview h2 {
  font-size: 20px;
  font-weight: bold;
  color: #333;
  margin: 20px 0 12px 0;
}

.markdown-preview h3 {
  font-size: 18px;
  font-weight: bold;
  color: #555;
  margin: 16px 0 8px 0;
}

.markdown-preview p {
  margin: 0 0 12px 0;
  text-align: justify;
}

.markdown-preview strong {
  font-weight: bold;
  color: #409eff;
}

.markdown-preview em {
  font-style: italic;
  color: #666;
}

.markdown-preview code {
  background: #f4f4f4;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}

.markdown-preview pre {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 12px;
  margin: 12px 0;
  overflow-x: auto;
}

.markdown-preview pre code {
  background: none;
  padding: 0;
  border-radius: 0;
}

.markdown-preview li {
  margin: 4px 0;
  padding-left: 8px;
}
</style>
