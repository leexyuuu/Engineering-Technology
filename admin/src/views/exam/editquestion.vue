<template>
  <div class="app-container">
    <el-form :model="form" :rules="rules" ref="form" label-width="100px">
      <el-form-item label="题目标题" prop="title">
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item label="题目类型" prop="type">
        <el-select v-model="form.type" placeholder="请选择题目类型">
          <el-option label="单选题" value="single" />
          <el-option label="多选题" value="multiple" />
          <el-option label="填空题" value="blank" />
        </el-select>
      </el-form-item>
      <el-form-item label="需要上传文件答题">
        <el-switch v-model="form.requires_file" />
      </el-form-item>
      <el-form-item label="文件说明" v-if="form.requires_file">
        <el-input v-model="form.file_description" />
      </el-form-item>
      <el-form-item label="问题列表">
        <div v-for="(problem, idx) in form.problems" :key="idx" style="margin-bottom: 20px; border: 1px solid #eee; padding: 10px;">
          <el-form-item :label="'问题' + (idx+1) + '内容'" :prop="'problems.'+idx+'.content'">
            <el-input v-model="problem.content" />
          </el-form-item>
          <el-form-item :label="'问题类型'" :prop="'problems.'+idx+'.type'">
            <el-select v-model="problem.type" placeholder="请选择问题类型">
              <el-option label="单选题" value="single" />
              <el-option label="多选题" value="multiple" />
              <el-option label="填空题" value="blank" />
            </el-select>
          </el-form-item>
          <div v-if="problem.type==='single'||problem.type==='multiple'">
            <el-form-item label="选项">
              <div v-for="(option, oidx) in problem.options" :key="oidx" style="display:flex;align-items:center;margin-bottom:5px;">
                <el-input v-model="option.text" placeholder="选项内容" style="width:200px;" />
                <el-checkbox v-model="option.is_correct" style="margin-left:10px;">正确</el-checkbox>
                <el-button type="text" @click="removeOption(idx, oidx)">删除</el-button>
              </div>
              <el-button type="primary" size="mini" @click="addOption(idx)">添加选项</el-button>
            </el-form-item>
          </div>
          <el-button type="danger" size="mini" @click="removeProblem(idx)">删除问题</el-button>
        </div>
        <el-button type="primary" @click="addProblem">添加问题</el-button>
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
export default {
  data() {
    return {
      form: {
        title: '',
        type: '',
        requires_file: false,
        file_description: '',
        problems: []
      },
      rules: {
        title: [{ required: true, message: '请输入题目标题', trigger: 'blur' }],
        type: [{ required: true, message: '请选择题目类型', trigger: 'change' }]
      },
      exam_id: null,
      question_id: null
    }
  },
  created() {
    this.exam_id = this.$route.params.exam_id
    this.question_id = this.$route.params.question_id
    if (this.question_id) {
      fetchExamQuestion(this.exam_id, this.question_id).then(res => {
        this.form = res.data || res
        if (!this.form.problems) this.form.problems = []
      })
    }
  },
  methods: {
    addProblem() {
      this.form.problems.push({ content: '', type: '', options: [] })
    },
    removeProblem(idx) {
      this.form.problems.splice(idx, 1)
    },
    addOption(problemIdx) {
      this.form.problems[problemIdx].options = this.form.problems[problemIdx].options || []
      this.form.problems[problemIdx].options.push({ text: '', is_correct: false })
    },
    removeOption(problemIdx, optionIdx) {
      this.form.problems[problemIdx].options.splice(optionIdx, 1)
    },
    onSubmit() {
      this.$refs.form.validate(valid => {
        if (!valid) return
        const action = this.question_id ? updateExamQuestion(this.exam_id, this.question_id, this.form) : createExamQuestion(this.exam_id, this.form)
        action.then(() => {
          this.$message.success('保存成功')
          this.$router.push({ path: `/exam/questionlist/${this.exam_id}` })
        })
      })
    }
  }
}
</script> 