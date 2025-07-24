<template>
  <div class="app-container">
    <el-form :model="form" :rules="rules" ref="form" label-width="120px">
      <el-form-item label="题目顺序" prop="order">
        <el-input v-model.number="form.order" type="number" style="width: 120px" />
      </el-form-item>
      <el-form-item label="题目描述" prop="content">
        <el-input v-model="form.content" type="textarea" :autosize="{ minRows: 2, maxRows: 6 }" />
      </el-form-item>
      <el-form-item label="需要上传文件答题">
        <el-switch v-model="form.requires_file" />
      </el-form-item>
      <el-form-item label="文件说明" v-if="form.requires_file">
        <el-input v-model="form.file_description" type="textarea" :autosize="{ minRows: 1, maxRows: 4 }" />
      </el-form-item>
      <el-form-item label="子问题列表">
        <div v-for="(sub, idx) in form.sub_questions" :key="sub.uuid" style="margin-bottom: 24px; border: 1px solid #eee; padding: 16px; border-radius: 4px;">
          <el-row :gutter="16">
            <el-col :span="6">
              <el-form-item :label="'顺序'" :prop="'sub_questions.'+idx+'.order'">
                <el-input v-model.number="sub.order" type="number" style="width: 80px" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item :label="'内容'" :prop="'sub_questions.'+idx+'.content'">
                <el-input v-model="sub.content" type="textarea" :autosize="{ minRows: 1, maxRows: 3 }" />
              </el-form-item>
            </el-col>
            <el-col :span="6">
              <el-form-item :label="'类型'" :prop="'sub_questions.'+idx+'.question_type'">
                <el-select v-model="sub.question_type" placeholder="请选择类型" style="width: 120px">
                  <el-option label="单选题" value="single_choice" />
                  <el-option label="多选题" value="multiple_choice" />
                  <el-option label="填空题" value="text" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="6">
              <el-form-item :label="'分值'" :prop="'sub_questions.'+idx+'.score'">
                <el-input v-model.number="sub.score" type="number" style="width: 80px" />
              </el-form-item>
            </el-col>
            <el-col :span="18">
              <div v-if="sub.question_type==='single_choice'||sub.question_type==='multiple_choice'">
                <el-form-item label="选项">
                  <div v-for="(opt, oidx) in sub.options" :key="opt.uuid" style="display:flex;align-items:center;margin-bottom:5px;">
                    <el-input v-model="opt.content" placeholder="选项内容" style="width:200px;" />
                    <el-checkbox v-model="opt.is_correct" style="margin-left:10px;">正确</el-checkbox>
                    <el-button type="text" @click="removeOption(idx, oidx)">删除</el-button>
                  </div>
                  <el-button type="primary" size="mini" @click="addOption(idx)">添加选项</el-button>
                </el-form-item>
              </div>
            </el-col>
          </el-row>
          <el-button type="danger" size="mini" @click="removeSubQuestion(idx)" style="margin-top:8px;">删除子问题</el-button>
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
import { fetchExamQuestion, createExamQuestion, updateExamQuestion } from '@/api/exam'
function uuid() {
  return '_' + Math.random().toString(36).substr(2, 9)
}
export default {
  data() {
    return {
      form: {
        order: 1,
        content: '',
        exam_id:'',
        uuid: uuid(),
        requires_file: false,
        file_description: '',
        sub_questions: []
      },
      rules: {
        content: [{ required: true, message: '请输入题目内容', trigger: 'blur' }]
      },
      exam_id: null,
      question_id: null
    }
  },
  created() {
    this.exam_id = this.$route.params.exam_id
    this.form.exam_id=this.exam_id
    this.question_id = this.$route.params.question_id
    if (this.question_id) {
      fetchExamQuestion(this.exam_id, this.question_id).then(res => {
        const data = res.data || res
        this.form = {
          ...data
        }
      })
    }
  },
  methods: {
    addSubQuestion() {
      this.form.sub_questions.push({
        order: this.form.sub_questions.length + 1,
        content: '',
        question_type: '',
        q_uuid:this.form.uuid,
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
      sub.options.push({ content: '', is_correct: false, uuid: uuid(),subq_uuid:sub.uuid })
    },
    removeOption(subIdx, optIdx) {
      this.form.sub_questions[subIdx].options.splice(optIdx, 1)
    },
    onSubmit() {
      this.$refs.form.validate(valid => {
        if (!valid) return
        // 提交时去除uuid辅助字段
        const submitData = {
          ...this.form,
          sub_questions_str: JSON.stringify(this.form.sub_questions)
        }
        submitData.sub_questions=null

        const action = this.question_id ? updateExamQuestion(this.question_id, submitData) : createExamQuestion(submitData)
        action.then(() => {
          this.$message.success('保存成功')
          this.$router.push({ path: `/exam/questionlist/${this.exam_id}` })
        })
      })
    }
  }
}
</script> 